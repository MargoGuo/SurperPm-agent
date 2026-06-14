"""Goal execution engine — orchestrates agent runs via KnowledgeStore."""

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.services import exec_env
from app.services.event_bus import (
    EXECUTION_COMPLETED,
    EXECUTION_PROGRESS,
    EXECUTION_STARTED,
    GOAL_UPDATED,
    bus,
)
from app.services.execution_lock import get_lock
from app.services.knowledge_store import get_store

_logger = logging.getLogger(__name__)

_cancel_events: dict[str, asyncio.Event] = {}
_pause_events: dict[str, asyncio.Event] = {}


def request_cancel(execution_id: str) -> bool:
    ev = _cancel_events.get(execution_id)
    if ev:
        ev.set()
        return True
    return False


def request_pause(execution_id: str) -> bool:
    ev = _pause_events.get(execution_id)
    if ev:
        ev.set()
        return True
    return False


def request_resume(execution_id: str) -> bool:
    ev = _pause_events.get(execution_id)
    if ev and ev.is_set():
        ev.clear()
        return True
    return False


def _knowledge_root() -> str:
    return os.getenv("KNOWLEDGE_REPO_PATH") or settings.knowledge_repo_path


def _read_text_if_exists(path: Path) -> str:
    root = (_knowledge_root() or "").strip()
    if not root:
        return ""
    full = Path(root) / path if not path.is_absolute() else path
    if full.is_file():
        return full.read_text(encoding="utf-8")
    return ""


def _session_dir(session_name: str) -> Path | None:
    root = (_knowledge_root() or "").strip()
    if not root:
        return None
    d = Path(root) / "sessions" / session_name
    return d if d.is_dir() else None


def _session_context_parts(session_name: str | None) -> list[str]:
    if not session_name:
        return []
    session_dir = _session_dir(session_name)
    if session_dir is None:
        return []

    parts = [f"\n## Session context: {session_name}"]
    notes_text = _read_text_if_exists(session_dir / "notes.md")
    if notes_text:
        parts.append("\n### IntentSpec")
        parts.append(notes_text)

    decisions_text = _read_text_if_exists(session_dir / "decisions.md")
    if decisions_text:
        parts.append("\n### Decisions")
        parts.append(decisions_text)

    conversation_text = _read_text_if_exists(session_dir / "conversation.md")
    if conversation_text:
        lines = [line for line in conversation_text.splitlines() if line.strip()]
        tail = "\n".join(lines[-12:])
        if tail:
            parts.append("\n### Conversation tail")
            parts.append(tail)

    return parts if len(parts) > 1 else []


async def compose_goal_context(
    workspace_id: str, goal: dict,
) -> str:
    """Assemble the prompt context for a goal execution."""
    parts = [f"# Goal: {goal.get('title', '')}"]
    if goal.get("description"):
        parts.append(f"\n{goal['description']}")
    parts.extend(_session_context_parts(goal.get("session_name")))

    store = get_store()
    goal_msgs = store.list_discussions(topic_id=None)
    goal_msgs = [
        m for m in goal_msgs
        if m.get("workspace_id") == workspace_id
        and m.get("goal_id") == goal.get("id")
    ]
    goal_msgs.sort(key=lambda m: m.get("created_at", ""))
    goal_msgs = goal_msgs[-30:]

    if len(goal_msgs) < 10:
        seen_ids = {m.get("id") for m in goal_msgs}
        standalone = store.list_discussions(topic_id=None)
        extra = [
            m for m in standalone
            if m.get("workspace_id") == workspace_id
            and m.get("goal_id") is None
            and m.get("id") not in seen_ids
        ]
        extra.sort(key=lambda m: m.get("created_at", ""))
        goal_msgs = extra[-10:] + goal_msgs

    if goal_msgs:
        parts.append("\n## Discussion context")
        for msg in goal_msgs:
            parts.append(f"[{msg.get('role', '')}] {msg.get('content', '')}")

    try:
        from app.services.knowledge_distiller import get_top_learnings

        learnings_text = get_top_learnings(budget_tokens=500)
        if learnings_text:
            parts.append("\n## Relevant learnings")
            parts.append(learnings_text)
    except Exception:
        pass

    return "\n".join(parts)


async def execute_goal(
    workspace_id: str, goal_id: int, execution_id: str | None = None,
) -> None:
    lock = get_lock(workspace_id)
    async with lock:
        await _run(workspace_id, goal_id, execution_id)


async def _notify_discuss(
    store,
    workspace_id: str,
    goal_id: int,
    message: str,
) -> None:
    try:
        disc = await store.create_discussion({
            "workspace_id": workspace_id,
            "goal_id": goal_id,
            "role": "system",
            "content": message,
        })
        await bus.emit("discussion_created", {
            "id": disc["id"],
            "workspace_id": workspace_id,
            "goal_id": goal_id,
            "role": "system",
            "content": message,
            "created_at": disc["created_at"],
        })
    except Exception:
        _logger.warning("Failed to notify discuss", exc_info=True)


async def _run(
    workspace_id: str,
    goal_id: int,
    pre_created_execution_id: str | None = None,
) -> None:
    execution_id: str | None = pre_created_execution_id
    exec_ctx: exec_env.ExecEnv | None = None
    logs_buffer: list[dict] = []
    store = get_store()

    try:
        goal = store.get("goals", goal_id)
        if not goal or goal.get("workspace_id") != workspace_id:
            _logger.warning(
                "Goal %d not found in workspace %s", goal_id, workspace_id,
            )
            return

        workspace = store.get("workspaces", workspace_id)
        if not workspace:
            _logger.warning("Workspace %s not found", workspace_id)
            return

        if execution_id:
            exe = store.get("executions", execution_id)
            if exe:
                await store.update("executions", execution_id, {
                    "status": "running",
                    "started_at": datetime.now(UTC).isoformat(),
                })
        else:
            exe = await store.create("executions", {
                "goal_id": goal_id,
                "workspace_id": workspace_id,
                "status": "running",
                "started_at": datetime.now(UTC).isoformat(),
                "token_budget": goal.get("token_budget"),
                "error": None,
            })
            execution_id = exe["id"]

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

        target = goal.get("target")
        if target and target != "local":
            await _execute_remote(
                store, target, context, workspace_id, goal_id,
                execution_id, logs_buffer, cancel_ev,
            )
            return

        from app.services.ai_key_resolver import (
            resolve_ai_base_url,
            resolve_ai_key,
            resolve_ai_model,
        )

        api_key = await resolve_ai_key()
        if not api_key:
            raise RuntimeError(
                "AI API key not configured (Settings → AI Model)",
            )
        base_url = await resolve_ai_base_url()
        model = await resolve_ai_model()

        exec_ctx = await exec_env.prepare_execution(goal, workspace)
        exec_ctx.env["CLAUDE_CONFIG_DIR"] = str(exec_ctx.workdir)
        exec_ctx.env["ANTHROPIC_API_KEY"] = api_key
        exec_ctx.env["ANTHROPIC_AUTH_TOKEN"] = ""
        exec_ctx.env["ANTHROPIC_MODEL"] = ""
        if base_url:
            exec_ctx.env["ANTHROPIC_BASE_URL"] = base_url
        prompt = f"/SuperPmAgent-core:goal {context}"

        import json as _json

        mcp_servers: dict = {}
        try:
            mcp_file = store._root.parent / "mcp" / "servers.json"
            if mcp_file.is_file():
                data = _json.loads(
                    mcp_file.read_text(encoding="utf-8"),
                )
                for name, cfg in (data.get("servers") or {}).items():
                    if not isinstance(cfg, dict):
                        continue
                    if not cfg.get("enabled", True):
                        continue
                    transport = cfg.get("transport", "stdio")
                    if transport == "stdio":
                        mcp_servers[name] = {
                            "command": cfg.get("command"),
                            "args": cfg.get("args", []),
                            "env": cfg.get("env", {}),
                        }
                    elif transport in ("sse", "http"):
                        mcp_servers[name] = {
                            "type": transport,
                            "url": cfg.get("url"),
                            "headers": cfg.get("headers", {}),
                        }
        except Exception:
            _logger.warning(
                "Failed to load MCP servers", exc_info=True,
            )

        from app.services.agent import (
            iter_log_lines,
            run_goal_agent,
            stream_event_log,
        )
        from app.services.agent.runner import usage_tokens

        token_total = 0

        async def _on_event(message):
            nonlocal token_total
            delta = usage_tokens(getattr(message, "usage", None))
            if delta:
                token_total += delta

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

            new_lines = iter_log_lines(message)
            if new_lines:
                logs_buffer.extend(new_lines)
            ws_lines = [
                ln for ln in new_lines
                if ln.get("kind") not in ("text", "thinking")
            ]
            if delta or ws_lines:
                await bus.emit(EXECUTION_PROGRESS, {
                    "execution_id": execution_id,
                    "goal_id": goal_id,
                    "workspace_id": workspace_id,
                    "token_used": token_total,
                    "logs": ws_lines,
                })

        prev_exes = store.list("executions", goal_id=goal_id)
        prev_session_id = None
        for pe in sorted(
            prev_exes,
            key=lambda e: e.get("finished_at", ""),
            reverse=True,
        ):
            sid = pe.get("session_id")
            if sid and str(pe.get("id")) != str(execution_id):
                prev_session_id = sid
                break

        agent_result = await run_goal_agent(
            goal_text=prompt,
            cwd=str(exec_ctx.workdir),
            env=exec_ctx.env,
            plugins=exec_ctx.plugins,
            mcp_servers=mcp_servers if mcp_servers else None,
            setting_sources=[],
            max_turns=50,
            model=model or None,
            continue_conversation=bool(prev_session_id),
            on_event=_on_event,
            cancel_token=cancel_ev,
            pause_event=pause_ev,
        )

        if cancel_ev.is_set():
            raise RuntimeError("Cancelled by user")

        now = datetime.now(UTC).isoformat()
        await store.update("executions", execution_id, {
            "status": "success",
            "finished_at": now,
            "token_used": agent_result.tokens_used,
            "session_id": agent_result.session_id,
            "pr_url": agent_result.pr_url,
            "branch": (
                agent_result.branch or f"SuperPmAgent/goal-{goal_id}"
            ),
            "summary": (
                f"Completed in {agent_result.iterations} iterations"
            ),
            "logs": logs_buffer,
        })
        await store.update("goals", goal_id, {"status": "review"})

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

        pr_part = f"\nPR: {agent_result.pr_url}" if agent_result.pr_url else ""
        await _notify_discuss(store, workspace_id, goal_id, (
            f"✅ Goal 执行完成 — {agent_result.iterations} 次迭代，"
            f"{agent_result.tokens_used} tokens{pr_part}"
        ))

    except Exception as e:
        _logger.error("Execution failed for goal %d: %s", goal_id, e)
        if execution_id:
            try:
                now = datetime.now(UTC).isoformat()
                await store.update("executions", execution_id, {
                    "status": "failed",
                    "finished_at": now,
                    "error": str(e),
                    "logs": logs_buffer,
                })
                await store.update("goals", goal_id, {"status": "failed"})
            except Exception:
                _logger.exception(
                    "Failed to update execution/goal status on error",
                )

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

        await _notify_discuss(store, workspace_id, goal_id, (
            f"❌ Goal 执行失败: {e}"
        ))

    finally:
        if execution_id:
            _cancel_events.pop(execution_id, None)
            _pause_events.pop(execution_id, None)
        if exec_ctx:
            exec_env.cleanup_keydir(exec_ctx.keydir)


async def _execute_remote(
    store, target, context, workspace_id, goal_id,
    execution_id, logs_buffer, cancel_ev,
):
    """Execute a Goal on a remote Agent via cc-connect API."""

    from app.routes.agents import _read_agents

    agents = _read_agents()
    agent = agents.get(target)
    if not agent:
        raise RuntimeError(f"Remote agent '{target}' not registered")

    url = agent["cc_api_url"]
    project = agent.get("project", "default")
    headers = {"Content-Type": "application/json"}
    if agent.get("cc_api_token"):
        headers["Authorization"] = f"Bearer {agent['cc_api_token']}"

    prompt = f"/SuperPmAgent-core:goal {context}"

    import httpx

    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(
            f"{url}/api/v1/projects/{project}/send",
            headers=headers,
            json={"session_key": f"goal-{goal_id}", "message": prompt},
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"cc-connect send failed: {r.status_code} {r.text[:200]}",
            )

    now = datetime.now(UTC).isoformat()
    await store.update("executions", execution_id, {
        "status": "success",
        "finished_at": now,
        "summary": f"Dispatched to remote agent '{target}'",
        "logs": logs_buffer,
    })
    await store.update("goals", goal_id, {"status": "review"})

    await bus.emit(EXECUTION_COMPLETED, {
        "execution_id": execution_id,
        "goal_id": goal_id,
        "workspace_id": workspace_id,
        "status": "success",
    })
    await bus.emit(GOAL_UPDATED, {
        "goal_id": goal_id,
        "workspace_id": workspace_id,
        "status": "review",
    })

    await _notify_discuss(store, workspace_id, goal_id, (
        f"✅ Goal 已派发到远程 Agent '{target}'"
    ))
