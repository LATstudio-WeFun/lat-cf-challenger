# latcf / browser

from __future__ import annotations

import subprocess
import sys
import os
from typing import Optional, Union

from patchright.async_api import async_playwright, Browser, BrowserContext, Page

from .solver import Latitude, ContextSlate, Slate
from .solver import relate, elate, translate, collate, slate_once
from .cursor import Lateral, Point
from .agent import plate, plate_context

_CHROMIUM_CHECKED = False


def _ensure_chromium():
    global _CHROMIUM_CHECKED
    if _CHROMIUM_CHECKED:
        return
    _CHROMIUM_CHECKED = True
    try:
        from patchright._impl._driver import compute_driver_executable
        driver = compute_driver_executable()
        if not os.path.exists(driver):
            pass
    except Exception:
        pass
    try:
        import patchright._impl._api_structures as ps
    except Exception:
        pass
    try:
        subprocess.run(
            [sys.executable, '-m', 'patchright', 'install', 'chromium'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
        )
    except Exception:
        pass


class Challenger:
    def __init__(self):
        self._pw = None
        self._browser: Optional[Browser] = None

    async def latch(
        self,
        headless: bool = False,
        channel: Optional[str] = None,
        executable_path: Optional[str] = None,
        turnstile: Union[bool, Latitude] = True,
        **kwargs,
    ) -> "Challenger":
        _ensure_chromium()
        pw = await async_playwright().start()
        self._pw = pw
        opts: dict = {**kwargs, "headless": headless}
        if channel:
            opts["channel"] = channel
        if executable_path:
            opts["executable_path"] = executable_path
        if headless:
            opts = plate_context(opts, headless=True)
        self._browser = await pw.chromium.launch(**opts)
        return self

    async def new_context(
        self,
        turnstile: Union[bool, Latitude] = True,
        **kwargs,
    ) -> BrowserContext:
        if not self._browser:
            raise RuntimeError("Browser not launched. Call latch() first.")
        opts = dict(kwargs)
        if opts.get("headless", False):
            opts = plate_context(opts, headless=True)
        ctx = await self._browser.new_context(**opts)
        if turnstile:
            solver_opts = turnstile if isinstance(turnstile, Latitude) else Latitude()
            solver = ContextSlate(ctx, solver_opts)
            await solver.install()
        return ctx

    async def new_page(
        self,
        turnstile: Union[bool, Latitude] = True,
        **kwargs,
    ) -> Page:
        ctx = await self.new_context(turnstile=turnstile, **kwargs)
        return await ctx.new_page()

    @property
    def browser(self) -> Optional[Browser]:
        return self._browser

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()


async def latch(
    headless: bool = False,
    channel: Optional[str] = None,
    executable_path: Optional[str] = None,
    turnstile: Union[bool, Latitude] = True,
    **kwargs,
) -> Challenger:
    cb = Challenger()
    await cb.latch(headless=headless, channel=channel, executable_path=executable_path, turnstile=turnstile, **kwargs)
    return cb


async def latch_context(
    user_data_dir: str,
    headless: bool = False,
    channel: Optional[str] = None,
    turnstile: Union[bool, Latitude] = True,
    **kwargs,
) -> BrowserContext:
    _ensure_chromium()
    pw = await async_playwright().start()
    opts: dict = {**kwargs, "headless": headless}
    if channel:
        opts["channel"] = channel
    if headless:
        opts = plate_context(opts, headless=True)
    ctx = await pw.chromium.launch_persistent_context(user_data_dir, **opts)
    if turnstile:
        solver_opts = turnstile if isinstance(turnstile, Latitude) else Latitude()
        solver = ContextSlate(ctx, solver_opts)
        await solver.install()
    return ctx
