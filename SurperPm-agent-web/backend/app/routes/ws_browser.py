from __future__ import annotations

import asyncio
import base64
import json
import logging
from http.cookies import SimpleCookie

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import session as session_svc
from app.services.browser_manager import browser_manager

log = logging.getLogger(__name__)

router = APIRouter()


def _extract_session_cookie(ws: WebSocket) -> str | None:
    raw = ws.headers.get("cookie", "")
    if not raw:
        return None
    cookie = SimpleCookie(raw)
    morsel = cookie.get("SuperPmAgent_session")
    return morsel.value if morsel else None


@router.websocket("/ws/browser/goal/{goal_id}")
async def ws_browser_goal(websocket: WebSocket, goal_id: int):
    await _ws_browser_handler(websocket, f"goal_{goal_id}")


@router.websocket("/ws/browser/{workspace_id}")
async def ws_browser(websocket: WebSocket, workspace_id: str):
    await _ws_browser_handler(websocket, workspace_id)


async def _ws_browser_handler(websocket: WebSocket, workspace_id: str):
    token = _extract_session_cookie(websocket)
    if not token:
        await websocket.close(code=4001, reason="no session cookie")
        return

    session = session_svc.decode(token)
    if not session:
        await websocket.close(code=4001, reason="invalid session")
        return

    user_id = session.get("user_id") or session.get("login", "anonymous")
    await websocket.accept()

    async def send_frame(data: bytes) -> None:
        try:
            await websocket.send_bytes(data)
        except Exception:
            pass

    async def send_navigated(url: str, title: str) -> None:
        try:
            await websocket.send_text(json.dumps({
                "type": "browser:navigated",
                "url": url,
                "title": title,
            }))
        except Exception:
            pass

    async def send_tabs() -> None:
        try:
            tabs, active = browser_manager.list_tabs(workspace_id, user_id)
            await websocket.send_text(json.dumps({
                "type": "browser:tabs",
                "tabs": tabs,
                "activeTabId": active,
            }))
        except Exception:
            pass

    async def send_download(filename: str, data: bytes) -> None:
        try:
            await websocket.send_text(json.dumps({
                "type": "browser:download",
                "filename": filename,
            }))
            await websocket.send_bytes(data)
        except Exception:
            pass

    try:
        # Cancel any pending cleanup from a previous disconnection
        browser_manager.cancel_cleanup(workspace_id, user_id)

        # Check if tabs already exist (reconnection scenario)
        existing_tabs = browser_manager.has_active_tabs(workspace_id, user_id)

        browser_manager.set_callbacks(
            workspace_id, user_id,
            on_frame=send_frame,
            on_navigated=send_navigated,
            on_tabs_changed=send_tabs,
            on_download=send_download,
        )

        if not existing_tabs:
            # First connection — create initial tab
            await browser_manager.create_tab(workspace_id, user_id)
        else:
            # Reconnection — restart screencast so frames flow to the new WebSocket
            try:
                await browser_manager.restart_active_screencast(workspace_id, user_id)
            except Exception:
                log.exception("ws_browser: failed to restart screencast on reconnection")
        # Send current tab state (works for both new and existing tabs)
        await send_tabs()

        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            try:
                if msg_type == "tab:new":
                    _, new_id = await browser_manager.create_tab(workspace_id, user_id)
                    await browser_manager.switch_tab(workspace_id, user_id, new_id)
                    await send_tabs()

                elif msg_type == "tab:switch":
                    await browser_manager.switch_tab(workspace_id, user_id, msg.get("tabId", ""))
                    await send_tabs()

                elif msg_type == "tab:close":
                    await browser_manager.close_tab(workspace_id, user_id, msg.get("tabId", ""))
                    await send_tabs()
                    tabs, _ = browser_manager.list_tabs(workspace_id, user_id)
                    if not tabs:
                        await browser_manager.create_tab(workspace_id, user_id)
                        await send_tabs()

                elif msg_type == "screenshot":
                    page = browser_manager.get_active_page(workspace_id, user_id)
                    if page:
                        asyncio.create_task(
                            _handle_screenshot_crop(websocket, page, msg)
                        )

                else:
                    page = browser_manager.get_active_page(workspace_id, user_id)
                    if not page:
                        continue
                    if msg_type == "navigate":
                        await browser_manager.navigate(page, msg.get("url", ""))
                    elif msg_type == "mouse":
                        await browser_manager.handle_mouse(page, msg)
                    elif msg_type == "scroll":
                        await browser_manager.handle_scroll(page, msg)
                    elif msg_type == "back":
                        await browser_manager.go_back(page)
                    elif msg_type == "forward":
                        await browser_manager.go_forward(page)
                    elif msg_type == "reload":
                        await browser_manager.reload(page)
                    elif msg_type == "key":
                        await browser_manager.handle_key(page, msg)
                    elif msg_type == "type":
                        await browser_manager.handle_type(page, msg)
                    elif msg_type == "resize":
                        await browser_manager.handle_resize(page, msg)
                    else:
                        log.warning("ws_browser: unknown message type %s", msg_type)

            except Exception as exc:
                log.exception("ws_browser: error handling %s", msg_type)
                await websocket.send_text(json.dumps({
                    "type": "browser:error",
                    "message": str(exc),
                }))

    except WebSocketDisconnect:
        log.info("ws_browser: client disconnected %s/%s — scheduling delayed cleanup", workspace_id, user_id)
    except Exception:
        log.exception("ws_browser: unexpected error")
    finally:
        # Schedule delayed cleanup — pages survive brief disconnections (e.g. route switches)
        browser_manager.schedule_cleanup(workspace_id, user_id, delay=30.0)


async def _handle_screenshot_crop(ws: WebSocket, page, msg: dict) -> None:
    x, y = msg.get("x", 0), msg.get("y", 0)
    w, h = msg.get("width", 0), msg.get("height", 0)

    try:
        clip = {"x": x, "y": y, "width": w, "height": h} if w > 0 and h > 0 else None
        png_bytes = await page.screenshot(type="png", clip=clip)
        img_b64 = base64.b64encode(png_bytes).decode()

        await ws.send_text(json.dumps({
            "type": "browser:screenshot_result",
            "imageBase64": img_b64,
        }))
    except Exception as exc:
        log.exception("screenshot crop failed")
        try:
            await ws.send_text(json.dumps({
                "type": "browser:error",
                "message": f"截图失败: {exc}",
            }))
        except Exception:
            pass
