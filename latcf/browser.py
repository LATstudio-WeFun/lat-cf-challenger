# latcf / browser

from __future__ import annotations

import subprocess
import sys
import os
import tempfile
from typing import Optional, Union, List

from patchright.async_api import async_playwright, Browser, BrowserContext, Page

from .solver import Latitude, ContextSlate, Slate
from .solver import relate, elate, translate, collate, slate_once
from .cursor import Lateral, Point
from .agent import plate, plate_context
from .stealth import get_stealth_js, get_launch_args, apply_stealth

_BROWSERS_CHECKED = False


def _ensure_browsers():
    global _BROWSERS_CHECKED
    if _BROWSERS_CHECKED:
        return
    _BROWSERS_CHECKED = True
    for browser in ['chromium', 'msedge']:
        try:
            subprocess.run(
                [sys.executable, '-m', 'patchright', 'install', browser],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=600,
            )
        except Exception:
            pass


def _resolve_channel(channel, executable_path):
    if channel or executable_path:
        return channel
    return "msedge"


class Challenger:
    def __init__(self):
        self._pw = None
        self._ctx: Optional[BrowserContext] = None
        self._headless = False
        self._ua: Optional[str] = None
        self._user_data_dir: Optional[str] = None
        self._owns_dir = False

    async def latch(
        self,
        headless: bool = False,
        channel: Optional[str] = None,
        executable_path: Optional[str] = None,
        turnstile: Union[bool, Latitude] = True,
        stealth: bool = True,
        user_data_dir: Optional[str] = None,
        **kwargs,
    ) -> "Challenger":
        _ensure_browsers()
        pw = await async_playwright().start()
        self._pw = pw
        self._headless = headless
        channel = _resolve_channel(channel, executable_path)

        opts: dict = {**kwargs, "headless": headless}
        if channel:
            opts["channel"] = channel
        if executable_path:
            opts["executable_path"] = executable_path

        opts["ignore_default_args"] = ["--enable-automation"]

        if stealth:
            existing_args: List[str] = opts.get("args", [])
            if isinstance(existing_args, list):
                opts["args"] = existing_args + get_launch_args()
            else:
                opts["args"] = get_launch_args()
        else:
            existing_args: List[str] = opts.get("args", [])
            if isinstance(existing_args, list):
                opts["args"] = existing_args + ["--disable-blink-features=AutomationControlled"]
            else:
                opts["args"] = ["--disable-blink-features=AutomationControlled"]

        if not headless and "no_viewport" not in opts:
            opts["no_viewport"] = True
        if headless:
            self._ua = plate(executable_path=executable_path, channel=channel)
            if self._ua and "user_agent" not in opts:
                opts["user_agent"] = self._ua

        if user_data_dir:
            self._user_data_dir = user_data_dir
        else:
            self._user_data_dir = os.path.join(tempfile.gettempdir(), "latcf_profile")
            self._owns_dir = True

        self._ctx = await pw.chromium.launch_persistent_context(self._user_data_dir, **opts)

        if stealth:
            await apply_stealth(self._ctx)
        if turnstile:
            solver_opts = turnstile if isinstance(turnstile, Latitude) else Latitude()
            solver = ContextSlate(self._ctx, solver_opts)
            await solver.install()

        return self

    async def new_page(self, **kwargs) -> Page:
        if not self._ctx:
            raise RuntimeError("Browser not launched. Call latch() first.")
        return await self._ctx.new_page()

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._ctx

    @property
    def pages(self) -> List[Page]:
        if self._ctx:
            return self._ctx.pages
        return []

    async def close(self):
        if self._ctx:
            await self._ctx.close()
        if self._pw:
            await self._pw.stop()


async def latch(
    headless: bool = False,
    channel: Optional[str] = None,
    executable_path: Optional[str] = None,
    turnstile: Union[bool, Latitude] = True,
    stealth: bool = True,
    user_data_dir: Optional[str] = None,
    **kwargs,
) -> Challenger:
    cb = Challenger()
    await cb.latch(headless=headless, channel=channel, executable_path=executable_path, turnstile=turnstile, stealth=stealth, user_data_dir=user_data_dir, **kwargs)
    return cb


async def latch_context(
    user_data_dir: str,
    headless: bool = False,
    channel: Optional[str] = None,
    turnstile: Union[bool, Latitude] = True,
    stealth: bool = True,
    **kwargs,
) -> BrowserContext:
    _ensure_browsers()
    pw = await async_playwright().start()
    channel = _resolve_channel(channel, kwargs.get("executable_path"))
    opts: dict = {**kwargs, "headless": headless}
    if channel:
        opts["channel"] = channel

    opts["ignore_default_args"] = ["--enable-automation"]

    if stealth:
        existing_args: List[str] = opts.get("args", [])
        if isinstance(existing_args, list):
            opts["args"] = existing_args + get_launch_args()
        else:
            opts["args"] = get_launch_args()
    else:
        existing_args: List[str] = opts.get("args", [])
        if isinstance(existing_args, list):
            opts["args"] = existing_args + ["--disable-blink-features=AutomationControlled"]
        else:
            opts["args"] = ["--disable-blink-features=AutomationControlled"]

    if not headless and "no_viewport" not in opts:
        opts["no_viewport"] = True
    if headless:
        ua = plate(channel=channel)
        if ua and "user_agent" not in opts:
            opts["user_agent"] = ua
    ctx = await pw.chromium.launch_persistent_context(user_data_dir, **opts)
    if stealth:
        await apply_stealth(ctx)
    if turnstile:
        solver_opts = turnstile if isinstance(turnstile, Latitude) else Latitude()
        solver = ContextSlate(ctx, solver_opts)
        await solver.install()
    return ctx
