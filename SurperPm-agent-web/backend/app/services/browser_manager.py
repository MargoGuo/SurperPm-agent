"""Browser management via Playwright, with Windows --reload workaround.

On Windows, uvicorn --reload forces a SelectorEventLoop that doesn't support
create_subprocess_exec.  When detected, Playwright runs on a dedicated
ProactorEventLoop thread and callers transparently bridge through it.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import sys
import threading
import uuid
from collections.abc import Awaitable, Callable

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

log = logging.getLogger(__name__)

_SCREENCAST_OPTS = {
    "format": "jpeg",
    "quality": 70,
    "maxWidth": 1280,
    "maxHeight": 960,
    "everyNthFrame": 2,
}


class _PWThread:
    """Dedicated thread + ProactorEventLoop for Playwright operations."""

    def __init__(self) -> None:
        self.loop = asyncio.ProactorEventLoop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    async def run(self, coro_factory):
        """Schedule *coro_factory()* on the dedicated loop, await the result."""
        return await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(coro_factory(), self.loop)
        )

    def shutdown(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)


class BrowserManager:
    def __init__(self) -> None:
        self._pw = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._pages: dict[tuple[str, str, str], Page] = {}
        self._cdp_sessions: dict[tuple[str, str, str], object] = {}
        self._page_info: dict[tuple[str, str, str], dict] = {}
        self._frame_cbs: dict[tuple[str, str], Callable[[bytes], Awaitable[None]]] = {}
        self._nav_cbs: dict[tuple[str, str], Callable[[str, str], Awaitable[None]]] = {}
        self._tabs_cbs: dict[tuple[str, str], Callable[[], Awaitable[None]]] = {}
        self._download_cbs: dict[tuple[str, str], Callable[[str, bytes], Awaitable[None]]] = {}
        self._active_tabs: dict[tuple[str, str], str] = {}
        self._pending_cleanup: dict[tuple[str, str], asyncio.Task] = {}
        # Windows SelectorEventLoop workaround
        self._pw_thread: _PWThread | None = None

    # ------------------------------------------------------------------
    # Internal helpers — bridge Playwright calls to the correct loop
    # ------------------------------------------------------------------

    def _needs_pw_thread(self) -> bool:
        return self._pw_thread is not None

    async def _pw_call(self, coro_factory):
        """Run a Playwright coroutine on the dedicated thread (if active)."""
        if self._pw_thread:
            return await self._pw_thread.run(coro_factory)
        return await coro_factory()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            if sys.platform == "win32" and type(loop).__name__ == "_WindowsSelectorEventLoop":
                log.info("BrowserManager: detected SelectorEventLoop — creating dedicated ProactorEventLoop thread")
                self._pw_thread = _PWThread()
                self._pw = await self._pw_thread.run(lambda: async_playwright().start())
                self._browser = await self._pw_thread.run(
                    lambda: self._pw.chromium.launch(headless=True)
                )
            else:
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=True)
            log.info("BrowserManager: Chromium launched")
        except Exception as exc:
            log.warning("BrowserManager: failed to launch (%s) — shared browser disabled", exc)
            self._pw = None
            self._browser = None

    async def stop(self) -> None:
        for task in self._pending_cleanup.values():
            if not task.done():
                task.cancel()
        self._pending_cleanup.clear()

        async def _do_stop():
            for key in list(self._pages):
                await self._remove_page(*key)
            for ctx in self._contexts.values():
                await ctx.close()
            self._contexts.clear()
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._pw:
                await self._pw.stop()
                self._pw = None
        await self._pw_call(_do_stop)
        if self._pw_thread:
            self._pw_thread.shutdown()
            self._pw_thread = None
        log.info("BrowserManager: shut down")

    # ------------------------------------------------------------------
    # Context / tab management
    # ------------------------------------------------------------------

    async def _get_context(self, workspace_id: str) -> BrowserContext:
        if self._browser is None:
            await self.start()
        if workspace_id not in self._contexts:
            assert self._browser is not None
            ctx = await self._pw_call(
                lambda: self._browser.new_context(
                    viewport={"width": 1280, "height": 960},
                    locale="en-US",
                    permissions=["clipboard-read", "clipboard-write"],
                )
            )
            async def _close_default():
                for p in ctx.pages:
                    await p.close()
            await self._pw_call(_close_default)
            self._contexts[workspace_id] = ctx
        return self._contexts[workspace_id]

    def set_callbacks(
        self,
        workspace_id: str,
        user_id: str,
        on_frame: Callable[[bytes], Awaitable[None]],
        on_navigated: Callable[[str, str], Awaitable[None]],
        on_tabs_changed: Callable[[], Awaitable[None]],
        on_download: Callable[[str, bytes], Awaitable[None]] | None = None,
    ) -> None:
        ukey = (workspace_id, user_id)
        self._frame_cbs[ukey] = on_frame
        self._nav_cbs[ukey] = on_navigated
        self._tabs_cbs[ukey] = on_tabs_changed
        if on_download:
            self._download_cbs[ukey] = on_download

    async def create_tab(
        self,
        workspace_id: str,
        user_id: str,
        tab_id: str | None = None,
    ) -> tuple[Page, str]:
        ukey = (workspace_id, user_id)
        if tab_id is None:
            tab_id = uuid.uuid4().hex[:8]

        pkey = (workspace_id, user_id, tab_id)
        if pkey in self._pages:
            return self._pages[pkey], tab_id

        async def _create():
            ctx = await self._get_context(workspace_id)
            page = await ctx.new_page()
            self._pages[pkey] = page
            self._page_info[pkey] = {"url": "about:blank", "title": ""}

            cdp = await ctx.new_cdp_session(page)
            self._cdp_sessions[pkey] = cdp

            async def _on_frame(params: dict) -> None:
                frame_data = base64.b64decode(params["data"])
                cb = self._frame_cbs.get(ukey)
                if cb:
                    try:
                        # Bridge callback back to the main loop
                        await self._bridge_to_main(cb(frame_data))
                    except Exception:
                        pass
                try:
                    await cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
                except Exception:
                    pass

            cdp.on("Page.screencastFrame", lambda params: asyncio.ensure_future(_on_frame(params)))

            def _on_nav(frame):
                if frame == page.main_frame:
                    asyncio.ensure_future(self._handle_nav(ukey, pkey, page))

            page.on("framenavigated", _on_nav)

            async def _on_download(download) -> None:
                try:
                    path = await download.path()
                    if path:
                        data = await asyncio.to_thread(self._read_file, str(path))
                        cb = self._download_cbs.get(ukey)
                        if cb:
                            await self._bridge_to_main(cb(download.suggested_filename, data))
                except Exception:
                    log.exception("BrowserManager: download handling failed")

            page.on("download", lambda dl: asyncio.ensure_future(_on_download(dl)))

            is_first = ukey not in self._active_tabs
            if is_first:
                self._active_tabs[ukey] = tab_id
                await cdp.send("Page.startScreencast", _SCREENCAST_OPTS)

            await page.goto("about:blank")
            log.info("BrowserManager: created tab %s for %s/%s", tab_id, workspace_id, user_id)
            return page, tab_id

        return await self._pw_call(_create)

    async def _bridge_to_main(self, coro):
        """Bridge an awaitable from the Playwright thread back to the main event loop."""
        if not self._needs_pw_thread():
            return await coro
        main_loop = asyncio.get_event_loop()
        return await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(coro, main_loop)
        )

    async def _handle_nav(
        self,
        ukey: tuple[str, str],
        pkey: tuple[str, str, str],
        page: Page,
    ) -> None:
        url = page.url
        try:
            title = await page.title()
        except Exception:
            title = ""
        self._page_info[pkey] = {"url": url, "title": title}

        tab_id = pkey[2]
        if self._active_tabs.get(ukey) == tab_id:
            cb = self._nav_cbs.get(ukey)
            if cb:
                await self._bridge_to_main(cb(url, title))

        tabs_cb = self._tabs_cbs.get(ukey)
        if tabs_cb:
            await self._bridge_to_main(tabs_cb())

    async def switch_tab(self, workspace_id: str, user_id: str, tab_id: str) -> Page | None:
        async def _do_switch():
            ukey = (workspace_id, user_id)
            pkey = (workspace_id, user_id, tab_id)
            if pkey not in self._pages:
                return None

            old_tab = self._active_tabs.get(ukey)
            if old_tab == tab_id:
                return self._pages[pkey]

            if old_tab:
                old_cdp = self._cdp_sessions.get((workspace_id, user_id, old_tab))
                if old_cdp:
                    try:
                        await old_cdp.send("Page.stopScreencast", {})
                    except Exception:
                        pass

            self._active_tabs[ukey] = tab_id
            new_cdp = self._cdp_sessions.get(pkey)
            if new_cdp:
                await new_cdp.send("Page.startScreencast", _SCREENCAST_OPTS)

            return self._pages[pkey]
        return await self._pw_call(_do_switch)

    async def close_tab(self, workspace_id: str, user_id: str, tab_id: str) -> None:
        async def _do_close():
            ukey = (workspace_id, user_id)
            pkey = (workspace_id, user_id, tab_id)
            if pkey not in self._pages:
                return

            was_active = self._active_tabs.get(ukey) == tab_id
            await self._remove_page(workspace_id, user_id, tab_id)

            if was_active:
                remaining = [
                    k[2] for k in self._pages if k[0] == workspace_id and k[1] == user_id
                ]
                if remaining:
                    await self.switch_tab(workspace_id, user_id, remaining[0])
                else:
                    self._active_tabs.pop(ukey, None)
        await self._pw_call(_do_close)

    def list_tabs(self, workspace_id: str, user_id: str) -> tuple[list[dict], str | None]:
        ukey = (workspace_id, user_id)
        active = self._active_tabs.get(ukey)
        tabs = []
        for (ws, uid, tid) in self._pages:
            if ws == workspace_id and uid == user_id:
                info = self._page_info.get((ws, uid, tid), {})
                tabs.append({"id": tid, "url": info.get("url", ""), "title": info.get("title", "")})
        return tabs, active

    def get_active_page(self, workspace_id: str, user_id: str) -> Page | None:
        ukey = (workspace_id, user_id)
        active = self._active_tabs.get(ukey)
        if active is None:
            return None
        return self._pages.get((workspace_id, user_id, active))

    async def _remove_page(self, workspace_id: str, user_id: str, tab_id: str) -> None:
        key = (workspace_id, user_id, tab_id)
        cdp = self._cdp_sessions.pop(key, None)
        if cdp:
            try:
                await cdp.send("Page.stopScreencast", {})
                await cdp.detach()
            except Exception:
                pass
        self._page_info.pop(key, None)
        page = self._pages.pop(key, None)
        if page:
            try:
                await page.close()
            except Exception:
                pass

    def cancel_cleanup(self, workspace_id: str, user_id: str) -> None:
        ukey = (workspace_id, user_id)
        task = self._pending_cleanup.pop(ukey, None)
        if task and not task.done():
            task.cancel()
            log.info("BrowserManager: cancelled pending cleanup for %s/%s", workspace_id, user_id)

    async def restart_active_screencast(self, workspace_id: str, user_id: str) -> None:
        """Restart screencast on the active tab (e.g. after WebSocket reconnection)."""
        ukey = (workspace_id, user_id)
        tab_id = self._active_tabs.get(ukey)
        if not tab_id:
            log.warning("restart_active_screencast: no active tab for %s/%s", workspace_id, user_id)
            return
        pkey = (workspace_id, user_id, tab_id)
        cdp = self._cdp_sessions.get(pkey)
        if not cdp:
            log.warning("restart_active_screencast: no CDP session for tab %s", tab_id)
            return

        async def _restart():
            try:
                await cdp.send("Page.stopScreencast", {})
            except Exception:
                pass
            await cdp.send("Page.startScreencast", _SCREENCAST_OPTS)
            log.info("restart_active_screencast: restarted for tab %s", tab_id)

        try:
            await self._pw_call(_restart)
        except Exception:
            log.exception("restart_active_screencast: failed for tab %s", tab_id)

    def has_active_tabs(self, workspace_id: str, user_id: str) -> bool:
        ukey = (workspace_id, user_id)
        return any(k[0] == workspace_id and k[1] == user_id for k in self._pages)

    async def remove_all_pages(self, workspace_id: str, user_id: str, check_cancelled: Callable[[], bool] | None = None) -> None:
        async def _do_remove():
            keys = [k for k in self._pages if k[0] == workspace_id and k[1] == user_id]
            for key in keys:
                if check_cancelled and check_cancelled():
                    log.info("BrowserManager: remove_all_pages cancelled mid-flight for %s/%s", workspace_id, user_id)
                    return
                await self._remove_page(*key)
            ukey = (workspace_id, user_id)
            self._frame_cbs.pop(ukey, None)
            self._nav_cbs.pop(ukey, None)
            self._tabs_cbs.pop(ukey, None)
            self._download_cbs.pop(ukey, None)
            self._active_tabs.pop(ukey, None)
        await self._pw_call(_do_remove)

    def schedule_cleanup(self, workspace_id: str, user_id: str, delay: float = 30.0) -> None:
        ukey = (workspace_id, user_id)
        self.cancel_cleanup(workspace_id, user_id)

        async def _delayed_remove():
            try:
                await asyncio.sleep(delay)
                # Check if a reconnection cancelled us during the sleep
                if ukey not in self._pending_cleanup:
                    return
                await self.remove_all_pages(
                    workspace_id, user_id,
                    check_cancelled=lambda: ukey not in self._pending_cleanup,
                )
                self._pending_cleanup.pop(ukey, None)
                log.info("BrowserManager: cleanup completed for %s/%s after %.0fs grace period",
                         workspace_id, user_id, delay)
            except asyncio.CancelledError:
                pass

        self._pending_cleanup[ukey] = asyncio.ensure_future(_delayed_remove())
        log.info("BrowserManager: scheduled cleanup for %s/%s in %.0fs",
                 workspace_id, user_id, delay)

    @staticmethod
    def _read_file(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    # ------------------------------------------------------------------
    # Page interaction — the Page object was already created on the
    # Playwright loop, so all calls must be bridged.
    # ------------------------------------------------------------------

    async def navigate(self, page: Page, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        async def _do():
            try:
                await page.goto(url, wait_until="commit", timeout=15000)
            except Exception as e:
                if "timeout" in str(e).lower():
                    log.warning("navigate timeout (page still loading): %s", url)
                else:
                    raise
        await self._pw_call(_do)

    async def go_back(self, page: Page) -> None:
        async def _do():
            await page.go_back(wait_until="domcontentloaded", timeout=15000)
        await self._pw_call(_do)

    async def go_forward(self, page: Page) -> None:
        async def _do():
            await page.go_forward(wait_until="domcontentloaded", timeout=15000)
        await self._pw_call(_do)

    async def reload(self, page: Page) -> None:
        async def _do():
            await page.reload(wait_until="domcontentloaded", timeout=15000)
        await self._pw_call(_do)

    async def handle_mouse(self, page: Page, data: dict) -> None:
        action = data.get("action", "click")
        x, y = data.get("x", 0), data.get("y", 0)
        button = data.get("button", "left")

        async def _do():
            if action == "move":
                await page.mouse.move(x, y)
            elif action == "click":
                await page.mouse.click(x, y, button=button)
            elif action == "dblclick":
                await page.mouse.dblclick(x, y, button=button)
            elif action == "down":
                await page.mouse.move(x, y)
                await page.mouse.down(button=button)
            elif action == "up":
                await page.mouse.move(x, y)
                await page.mouse.up(button=button)
        await self._pw_call(_do)

    async def handle_scroll(self, page: Page, data: dict) -> None:
        x, y = data.get("x", 0), data.get("y", 0)
        dx, dy = data.get("deltaX", 0), data.get("deltaY", 0)
        async def _do():
            await page.mouse.move(x, y)
            await page.evaluate(f"window.scrollBy({dx}, {dy})")
        await self._pw_call(_do)

    async def handle_key(self, page: Page, data: dict) -> None:
        async def _do():
            key = data.get("key", "")
            modifiers = data.get("modifiers", [])
            for mod in modifiers:
                await page.keyboard.down(mod)
            await page.keyboard.press(key)
            for mod in reversed(modifiers):
                await page.keyboard.up(mod)
        await self._pw_call(_do)

    async def handle_type(self, page: Page, data: dict) -> None:
        async def _do():
            text = data.get("text", "")
            if text:
                await page.keyboard.type(text)
        await self._pw_call(_do)

    async def handle_resize(self, page: Page, data: dict) -> None:
        width = data.get("width", 1280)
        height = data.get("height", 960)
        async def _do():
            await page.set_viewport_size({"width": width, "height": height})
            key = None
            for k, p in self._pages.items():
                if p == page:
                    key = k
                    break
            if key:
                cdp = self._cdp_sessions.get(key)
                if cdp:
                    await cdp.send("Page.stopScreencast", {})
                    opts = {**_SCREENCAST_OPTS}
                    if width:
                        opts["maxWidth"] = width
                    if height:
                        opts["maxHeight"] = height
                    await cdp.send("Page.startScreencast", {
                        **opts,
                    })
        await self._pw_call(_do)


browser_manager = BrowserManager()
