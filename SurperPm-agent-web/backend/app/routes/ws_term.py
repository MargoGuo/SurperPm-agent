"""Interactive PTY terminal over WebSocket, scoped to a goal's workdir.

Lets a user open a real shell in the goal's cloned working directory
(`data/repos/<workspace>/goal-<id>`) to inspect what the agent changed, run
tests, or debug. Mirrors the loopat terminal protocol: JSON frames
`{type: data|resize}` client->server and `{type: data|exit|error}` server->client.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from http.cookies import SimpleCookie
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import exec_env
from app.services import session as session_svc
from app.services.knowledge_store import get_store
from app.services.platform import IS_WIN

if not IS_WIN:
    import fcntl
    import pty
    import struct
    import termios

log = logging.getLogger(__name__)

router = APIRouter()


def _extract_session_cookie(ws: WebSocket) -> str | None:
    raw = ws.headers.get("cookie", "")
    if not raw:
        return None
    cookie = SimpleCookie(raw)
    morsel = cookie.get("SuperPmAgent_session")
    return morsel.value if morsel else None


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    if IS_WIN:
        return
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass


@router.websocket("/ws/goal/{goal_id}/term")
async def ws_goal_term(websocket: WebSocket, goal_id: int):
    token = _extract_session_cookie(websocket)
    session = session_svc.decode(token) if token else None
    if not session:
        await websocket.close(code=4001, reason="invalid session")
        return

    store = get_store()
    goal = store.get("goals", goal_id)
    if not goal:
        await websocket.close(code=4004, reason="goal not found")
        return

    workdir = exec_env.workdir_for(goal.get("workspace_id", ""), goal_id)
    cwd = str(workdir) if workdir.is_dir() else str(Path.home())

    await websocket.accept()

    if IS_WIN:
        await websocket.send_text(json.dumps({
            "type": "data",
            "data": "\x1b[31m[Terminal not supported on Windows]\x1b[0m\r\n",
        }))
        await websocket.close()
        return

    if not workdir.is_dir():
        await websocket.send_text(json.dumps({
            "type": "data",
            "data": (
                f"\x1b[2m[workdir {workdir} not found - goal has not run yet; "
                f"falling back to {cwd}]\x1b[0m\r\n"
            ),
        }))

    shell = os.environ.get("SHELL", "/bin/bash")
    master_fd, slave_fd = pty.openpty()

    def _preexec() -> None:
        os.setsid()
        try:
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        except OSError:
            pass

    env = {
        **os.environ,
        "TERM": "xterm-256color",
        "SuperPmAgent_GOAL_ID": str(goal_id),
        "SuperPmAgent_WORKSPACE": goal.get("workspace_id", ""),
    }

    try:
        proc = await asyncio.create_subprocess_exec(
            shell, "-i",
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            cwd=cwd, env=env, preexec_fn=_preexec,
        )
    except Exception as exc:
        log.exception("ws_term: failed to spawn shell")
        await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        os.close(master_fd)
        os.close(slave_fd)
        await websocket.close()
        return

    os.close(slave_fd)
    loop = asyncio.get_event_loop()

    async def _pty_to_ws() -> None:
        while True:
            try:
                data = await loop.run_in_executor(None, os.read, master_fd, 65536)
            except OSError:
                break
            if not data:
                break
            await websocket.send_text(json.dumps({
                "type": "data",
                "data": data.decode(errors="replace"),
            }))

    async def _ws_to_pty() -> None:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "data":
                os.write(master_fd, msg.get("data", "").encode())
            elif mtype == "resize":
                _set_winsize(master_fd, int(msg.get("rows", 24)), int(msg.get("cols", 80)))

    pump = asyncio.create_task(_pty_to_ws())
    try:
        await _ws_to_pty()
    except (WebSocketDisconnect, json.JSONDecodeError, RuntimeError):
        pass
    except Exception:
        log.exception("ws_term: receive loop error")
    finally:
        pump.cancel()
        try:
            await websocket.send_text(json.dumps({"type": "exit", "code": 0}))
        except Exception:
            pass
        if proc.returncode is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            await proc.wait()
        os.close(master_fd)
