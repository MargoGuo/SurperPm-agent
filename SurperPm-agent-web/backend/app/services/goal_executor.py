"""Goal execution engine V2 — orchestrates agent runs via DB-backed Execution rows."""
import asyncio
import logging
from datetime import UTC, datetime

from sqlmodel import select

from app.database import async_session
from app.models.discussion import Discussion
from app.models.execution import Execution
from app.models.goal import Goal
from app.models.workspace import Workspace
from app.services import exec_env
from app.services.event_bus import (
    EXECUTION_COMPLETED,
    EXECUTION_PROGRESS,
    EXECUTION_STARTED,
    GOAL_UPDATED,
    bus,
)
from app.services.execution_lock import get_lock

_logger = logging.getLogger(__name__)

# Cancel signals for in-flight executions, keyed by execution_id.
_cancel_events: dict[str, asyncio.Event] = {}
# Pause signals — set() pauses the agent loop, clear() resumes it.
_pause_events: dict[str, asyncio.Event] = {}


def request_cancel(execution_id: str) -> bool:
    """Signal a running execution to stop. Returns True if it was in-flight."""
    ev = _cancel_events.get(execution_id)
    if ev is None:
        return False
    ev.set()
    return True


def request_pause(execution_id: str) -> bool:
    """Pause an in-flight execution. Returns True if it was in-flight."""
    ev = _pause_events.get(execution_id)
    if ev is None:
        return False
    ev.set()
    return True


def request_resume(execution_id: str) -> bool:
    """Resume a paused execution. Returns True if it was in-flight."""
    ev = _pause_events.get(execution_id)
    if ev is None:
        return False
    ev.clear()
    return True


def is_paused(execution_id: str) -> bool:
    """Whether an in-flight execution is currently paused."""
    ev = _pause_events.get(execution_id)
    return ev is not None and ev.is_set()


async def compose_goal_context(workspace_id: str, goal: Goal) -> str:
    """Assemble the prompt context for a goal execution."""
    parts = [f"# Goal: {goal.title}"]
    if goal.description:
        parts.append(f"\n{goal.description}")

    async with async_session() as db:
        stmt = (
            select(Discussion)
            .where(
                Discussion.workspace_id == workspace_id,
                Discussion.goal_id == goal.id,
            )
            .order_by(Discussion.created_at.desc())
            .limit(30)
        )
        result = await db.execute(stmt)
        goal_msgs = list(reversed(result.scalars().all()))

        if len(goal_msgs) < 10:
            seen_ids = {m.id for m in goal_msgs}
            stmt2 = (
                select(Discussion)
                .where(
                    Discussion.workspace_id == workspace_id,
                    Discussion.goal_id.is_(None),
                )
                .order_by(Discussion.created_at.desc())
                .limit(10)
            )
            result2 = await db.execute(stmt2)
            extra = [m for m in reversed(result2.scalars().all()) if m.id not in seen_ids]
            goal_msgs = extra + goal_msgs

    if goal_msgs:
        parts.append("\n## Discussion context")
        for msg in goal_msgs:
            parts.append(f"[{msg.role}] {msg.content}")

    return "\n".join(parts)


async def execute_goal(workspace_id: str, goal_id: int, execution_id: str | None = None) -> None:
    """Background task: run agent for a goal. Serialised per workspace."""
    lock = get_lock(workspace_id)
    async with lock:
        await _run(workspace_id, goal_id, execution_id)


async def _run(workspace_id: str, goal_id: int, pre_created_execution_id: str | None = None) -> None:
    execution_id: str | None = pre_created_execution_id
    exec_ctx: exec_env.ExecEnv | None = None
    logs_buffer: list[dict] = []
    try:
        async with async_session() as db:
            stmt = select(Goal).where(
                Goal.id == goal_id, Goal.workspace_id == workspace_id
            )
            result = await db.execute(stmt)
            goal = result.scalar_one_or_none()
            if not goal:
                _logger.warning("Goal %d not found in workspace %s", goal_id, workspace_id)
                return

            workspace = await db.get(Workspace, workspace_id)
            if not workspace:
                _logger.warning("Workspace %s not found", workspace_id)
                return

            if execution_id:
                # Reuse pre-created execution row — just update status to running
                exec_row = await db.get(Execution, execution_id)
                if exec_row:
                    exec_row.status = "running"
                    exec_row.started_at = datetime.now(UTC)
                    db.add(exec_row)
                    await db.commit()
            else:
                execution = Execution(
                    goal_id=goal_id,
                    workspace_id=workspace_id,
                    status="running",
                    started_at=datetime.now(UTC),
                    token_budget=goal.token_budget,
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)
                execution_id = execution.id

        cancel_ev = asyncio.Event()
        _cancel_events[execution_id] = cancel_ev
        pause_ev = asyncio.Event()
        _pause_events[execution_id] = pause_ev

        await bus.emit(EXECUTION_STARTED, {
            "execution_id": execution_id,
            "goal_id": goal_id,
            "workspace_id": workspace_id,
        })

        context = await compose_goal_context(workspace_id, goal)

        from app.services.ai_key_resolver import (
            resolve_ai_base_url,
            resolve_ai_key,
            resolve_ai_model,
        )

        api_key = await resolve_ai_key()
        if not api_key:
            raise RuntimeError("AI API key not configured (Settings → AI Model)")
        base_url = await resolve_ai_base_url()
        model = await resolve_ai_model()

        # Clone the repo via SSH, inject git/gh creds, resolve plugin dirs.
        exec_ctx = await exec_env.prepare_execution(goal, workspace)
        # Inject our resolved AI auth by value, and neutralise any ANTHROPIC_*
        # inherited from the deploy environment (systemd/shell) so a stray
        # AUTH_TOKEN/MODEL can't override the key we send to the configured
        # provider. setting_sources=[] already blocks ~/.claude/settings.json;
        # this covers process-env inheritance for the multi-tenant server.
        # Also isolate CLAUDE_CONFIG_DIR to the goal's workdir so the host
        # machine's ~/.claude/ can never leak into the subprocess.
        exec_ctx.env["CLAUDE_CONFIG_DIR"] = str(exec_ctx.workdir)
        exec_ctx.env["ANTHROPIC_API_KEY"] = api_key
        exec_ctx.env["ANTHROPIC_AUTH_TOKEN"] = ""
        exec_ctx.env["ANTHROPIC_MODEL"] = ""
        if base_url:
            exec_ctx.env["ANTHROPIC_BASE_URL"] = base_url
        prompt = f"/SuperPmAgent-core:goal {context}"

        # Resolve enabled MCP servers for this workspace
        import json as _json

        from app.models.mcp_server import MCPServer

        mcp_servers: dict = {}
        async with async_session() as db:
            mcp_stmt = select(MCPServer).where(
                MCPServer.workspace_id == workspace_id,
                MCPServer.enabled == True,
            )
            mcp_result = await db.execute(mcp_stmt)
            for srv in mcp_result.scalars().all():
                try:
                    if srv.transport == "stdio":
                        mcp_servers[srv.name] = {
                            "command": srv.command,
                            "args": _json.loads(srv.args) if srv.args else [],
                            "env": _json.loads(srv.env) if srv.env else {},
                        }
                    elif srv.transport == "sse":
                        mcp_servers[srv.name] = {
                            "type": "sse",
                            "url": srv.url,
                            "headers": _json.loads(srv.headers) if srv.headers else {},
                        }
                    elif srv.transport == "http":
                        mcp_servers[srv.name] = {
                            "type": "http",
                            "url": srv.url,
                            "headers": _json.loads(srv.headers) if srv.headers else {},
                        }
                except Exception:
                    _logger.warning("Failed to build MCP config for server %s", srv.name, exc_info=True)

        from app.services.agent import iter_log_lines, run_goal_agent, stream_event_log

        token_total = 0

        from app.services.agent.runner import usage_tokens

        async def _on_event(message):
            nonlocal token_total
            delta = usage_tokens(getattr(message, "usage", None))
            if delta:
                token_total += delta

            # Incremental StreamEvent (text/thinking delta): forward to the WS
            # only. The terminal full message carries the finalized copy that we
            # persist to execution.logs, so we don't buffer deltas here.
            stream_line = stream_event_log(message)
            if stream_line is not None:
                await bus.emit(EXECUTION_PROGRESS, {
                    "execution_id": execution_id,
                    "goal_id": goal_id,
                    "workspace_id": workspace_id,
                    "token_used": token_total,
                    "logs": [stream_line],
                })
                return

            # Full message: persist every line to the DB buffer, but only stream
            # tool_use / tool_result / error to the WS — text & thinking already
            # went out as deltas above, so re-emitting would duplicate them.
            new_lines = iter_log_lines(message)
            if new_lines:
                logs_buffer.extend(new_lines)
            ws_lines = [ln for ln in new_lines if ln.get("kind") not in ("text", "thinking")]
            if delta or ws_lines:
                await bus.emit(EXECUTION_PROGRESS, {
                    "execution_id": execution_id,
                    "goal_id": goal_id,
                    "workspace_id": workspace_id,
                    "token_used": token_total,
                    "logs": ws_lines,
                })

        agent_result = await run_goal_agent(
            goal_text=prompt,
            cwd=str(exec_ctx.workdir),
            env=exec_ctx.env,
            plugins=exec_ctx.plugins,
            mcp_servers=mcp_servers if mcp_servers else None,
            # Isolate from host ~/.claude/settings.json env (its ANTHROPIC_*
            # vars point at a different provider and would override our keys).
            setting_sources=[],
            max_turns=50,
            model=model or None,
            on_event=_on_event,
            cancel_token=cancel_ev,
            pause_event=pause_ev,
        )

        if cancel_ev.is_set():
            raise RuntimeError("Cancelled by user")

        async with async_session() as db:
            stmt = select(Execution).where(Execution.id == execution_id)
            result = await db.execute(stmt)
            execution = result.scalar_one()
            execution.status = "success"
            execution.finished_at = datetime.now(UTC)
            execution.token_used = agent_result.tokens_used
            execution.pr_url = agent_result.pr_url
            execution.branch = agent_result.branch or f"SuperPmAgent/goal-{goal_id}"
            execution.summary = f"Completed in {agent_result.iterations} iterations"
            execution.logs = logs_buffer
            db.add(execution)

            stmt2 = select(Goal).where(Goal.id == goal_id)
            result2 = await db.execute(stmt2)
            goal = result2.scalar_one()
            goal.status = "review"
            db.add(goal)

            await db.commit()
            await db.refresh(execution)
            await db.refresh(goal)

        await bus.emit(EXECUTION_COMPLETED, {
            "execution_id": execution_id,
            "goal_id": goal_id,
            "workspace_id": workspace_id,
            "status": "success",
            "token_used": agent_result.tokens_used,
        })
        await bus.emit(GOAL_UPDATED, {
            "goal_id": goal_id,
            "workspace_id": workspace_id,
            "status": "review",
        })

    except Exception as e:
        _logger.error("Execution failed for goal %d: %s", goal_id, e)
        if execution_id:
            try:
                async with async_session() as db:
                    stmt = select(Execution).where(Execution.id == execution_id)
                    result = await db.execute(stmt)
                    execution = result.scalar_one_or_none()
                    if execution:
                        execution.status = "failed"
                        execution.finished_at = datetime.now(UTC)
                        execution.error = str(e)
                        execution.logs = logs_buffer
                        db.add(execution)

                    stmt2 = select(Goal).where(Goal.id == goal_id)
                    result2 = await db.execute(stmt2)
                    goal = result2.scalar_one_or_none()
                    if goal:
                        goal.status = "failed"
                        db.add(goal)

                    await db.commit()
            except Exception:
                _logger.exception("Failed to update execution/goal status on error")

        await bus.emit(EXECUTION_COMPLETED, {
            "execution_id": execution_id,
            "goal_id": goal_id,
            "workspace_id": workspace_id,
            "status": "failed",
            "error": str(e),
        })
        await bus.emit(GOAL_UPDATED, {
            "goal_id": goal_id,
            "workspace_id": workspace_id,
            "status": "failed",
        })

    finally:
        if execution_id:
            _cancel_events.pop(execution_id, None)
            _pause_events.pop(execution_id, None)
        if exec_ctx:
            exec_env.cleanup_keydir(exec_ctx.keydir)
