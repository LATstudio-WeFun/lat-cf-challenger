# latcf / solver

import asyncio
import random
import re
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict

from patchright.async_api import Page, BrowserContext, Locator, ElementHandle

from .cursor import Lateral, Point, Box

_TURNSTILE_SEL = [
    'iframe[src*="challenges.cloudflare.com"]',
    'iframe[title*="Cloudflare"]',
    'iframe[title*="challenge"]',
    ".cf-turnstile",
    "[data-sitekey]",
    '[name="cf-turnstile-response"]',
    'input[name="cf-turnstile-response"]',
    'textarea[name="cf-turnstile-response"]',
    'input[name="turnstile-response"]',
    'textarea[name="turnstile-response"]',
    'input[name="turnstile-token"]',
    'textarea[name="turnstile-token"]',
    "[data-cf-turnstile-response]",
    "[data-turnstile-response]",
    "[data-turnstile-token]",
]

_RESP_SEL = [
    '[name="cf-turnstile-response"]',
    'input[name="cf-turnstile-response"]',
    'textarea[name="cf-turnstile-response"]',
    'input[name="turnstile-response"]',
    'textarea[name="turnstile-response"]',
    'input[name="turnstile-token"]',
    'textarea[name="turnstile-token"]',
    "[data-cf-turnstile-response]",
    "[data-turnstile-response]",
    "[data-turnstile-token]",
]

_CF_FIELD = (
    'input[name*="cf-" i], input[name*="cf_" i], input[name*="turnstile" i], '
    'textarea[name*="cf-" i], textarea[name*="cf_" i], textarea[name*="turnstile" i], '
    "[data-ray], [data-cf-ray], [data-sitekey], [data-cf-turnstile-response]"
)

_FALLBACK = ["iframe", "div", "button", '[role="checkbox"]']
_FALL_LIMIT = 80
_MIN_TOK = 20


@dataclass
class Latitude:
    timeout_ms: int = 3000
    interval_ms: int = 500
    selectors: List[str] = field(default_factory=lambda: list(_TURNSTILE_SEL))
    max_candidates: int = 5
    foreground: bool = True
    click_delay_ms: int = 35
    mouse_move_steps: int = 8
    wait_after_click_ms: int = 100
    click_cooldown_ms: int = 5000
    max_click_cooldown_ms: int = 45000
    managed_timeout_ms: int = 45000
    logger: Optional[Callable[[str], None]] = None


@dataclass
class CFCookie:
    name: str
    value: str
    domain: Optional[str] = None
    path: Optional[str] = None
    expires: Optional[float] = None


@dataclass
class TurnstileResp:
    source: str
    value: str


@dataclass
class TurnstileWidget:
    sitekey: Optional[str] = None
    action: Optional[str] = None
    c_data: Optional[str] = None
    callback: Optional[str] = None
    theme: Optional[str] = None
    size: Optional[str] = None
    language: Optional[str] = None


@dataclass
class CFField:
    name: Optional[str] = None
    value: str = ""


@dataclass
class StorageEntry:
    key: str
    value: str


@dataclass
class CFData:
    url: str = ""
    user_agent: str = ""
    document_cookie_names: List[str] = field(default_factory=list)
    cookies: List[CFCookie] = field(default_factory=list)
    cf_cookies: List[CFCookie] = field(default_factory=list)
    clearance: str = ""
    cf_clearance: str = ""
    turnstile_present: bool = False
    turnstile_solved: bool = False
    turnstile_tokens: List[str] = field(default_factory=list)
    turnstile_responses: List[TurnstileResp] = field(default_factory=list)
    turnstile_sitekeys: List[str] = field(default_factory=list)
    turnstile_widgets: List[TurnstileWidget] = field(default_factory=list)
    turnstile_iframes: List[str] = field(default_factory=list)
    turnstile_scripts: List[str] = field(default_factory=list)
    challenge_cleared: bool = False
    challenge_managed: bool = False
    challenge_fields: List[CFField] = field(default_factory=list)
    challenge_ray_ids: List[str] = field(default_factory=list)
    storage_local: List[StorageEntry] = field(default_factory=list)
    storage_session: List[StorageEntry] = field(default_factory=list)


def _is_turnstile_box(box: Box) -> bool:
    return 260 <= box.width <= 340 and 35 <= box.height <= 90


def _click_pt(box: Box) -> Point:
    x_base = 30 if box.width > 80 else box.width / 2
    x_noise = (random.random() - 0.5) * min(8, box.width * 0.06)
    y_noise = (random.random() - 0.5) * min(6, box.height * 0.08)
    return Point(box.x + x_base + x_noise, box.y + box.height / 2 + y_noise)


async def _is_managed(page: Page) -> bool:
    try:
        return await page.evaluate("""() => {
            const t = (document.title || '') + '\\n' + (document.body?.innerText?.slice(0, 5000) || '') + '\\n' + document.body?.innerHTML?.slice(0, 3000) + '\\n' + location.href;
            const hasChallenge = /just a moment|security verification|checking your browser|正在安全验证|安全检查|请验证你是否为真人|请稍候|verify you are human|checking.*browser|attention required/i.test(t);
            const hasCf = /cloudflare|verify you are not a bot|malicious bots|ray id|__cf_chl_rt_tk|cf-challenge|challenge-platform/i.test(t);
            if (hasChallenge && hasCf) return true;
            if (hasChallenge && document.querySelector('script[src*="challenges.cloudflare.com"]')) return true;
            if (hasChallenge && document.querySelector('#challenge-running, #challenge-stage, .challenge-running')) return true;
            if (/__cf_chl_rt_tk/.test(location.href) && hasChallenge) return true;
            if (hasChallenge && document.querySelector('iframe[src*="challenges.cloudflare.com"], iframe[src*="cdn-cgi/challenge-platform"]')) return true;
            if (document.querySelector('iframe[src*="challenges.cloudflare.com"]') && /请稍候|just a moment|安全/i.test(document.title || '')) return true;
            return false;
        }""")
    except Exception:
        return False


async def _frame_ready(loc: Locator) -> bool:
    try:
        tag = await loc.evaluate("el => el.tagName?.toLowerCase() || ''")
        if tag == "iframe":
            frame = await loc.content_frame
            if not frame:
                return False
            try:
                await frame.wait_for_selector('input[type="checkbox"]', state="visible", timeout=3000)
            except Exception:
                pass
    except Exception:
        pass
    return True


async def _prep_click(page: Page, foreground: bool):
    if not foreground:
        return
    await page.wait_for_timeout(round(20 + random.random() * 40))
    await page.bring_to_front()
    try:
        await page.evaluate("() => { window.focus(); document.body?.focus?.(); }")
    except Exception:
        pass


async def _click_box(page: Page, box: Box, cursor: Lateral, opts: Latitude) -> bool:
    if box.width <= 0 or box.height <= 0:
        return False
    pt = _click_pt(box)
    await _prep_click(page, opts.foreground)
    if random.random() < 0.6:
        wx = pt.x + (random.random() - 0.5) * 120
        wy = pt.y + (random.random() - 0.5) * 80
        await cursor.move_to(Point(wx, wy), speed=0.7 + random.random() * 0.6)
        await page.wait_for_timeout(round(80 + random.random() * 200))
    await page.wait_for_timeout(round(30 + random.random() * 120))
    steps = max(1, opts.mouse_move_steps + round((random.random() - 0.5) * 4))
    await cursor.click(pt, speed=max(1, steps), overshoot_threshold=420, hesitate=round(20 + random.random() * 60), hold_ms=opts.click_delay_ms + round((random.random() - 0.5) * 16))
    if opts.wait_after_click_ms > 0:
        await page.wait_for_timeout(round(opts.wait_after_click_ms * (0.7 + random.random() * 0.6)))
    return True


async def _click_loc(page: Page, loc: Locator, cursor: Lateral, opts: Latitude) -> bool:
    try:
        bd = await loc.bounding_box(timeout=1000)
    except Exception:
        return False
    if not bd:
        return False
    box = Box(**bd)
    if not await _frame_ready(loc):
        return False
    pt = _click_pt(box)
    await _prep_click(page, opts.foreground)
    if random.random() < 0.6:
        wx = pt.x + (random.random() - 0.5) * 120
        wy = pt.y + (random.random() - 0.5) * 80
        try:
            await cursor.move_to(Point(wx, wy), speed=0.7 + random.random() * 0.6)
            await page.wait_for_timeout(round(80 + random.random() * 200))
        except Exception:
            pass
    await page.wait_for_timeout(round(30 + random.random() * 120))
    try:
        await cursor.click(pt, speed=max(1, opts.mouse_move_steps), overshoot_threshold=420, hesitate=round(20 + random.random() * 60), hold_ms=opts.click_delay_ms + round((random.random() - 0.5) * 16))
        if opts.wait_after_click_ms > 0:
            await page.wait_for_timeout(round(opts.wait_after_click_ms * (0.7 + random.random() * 0.6)))
        return True
    except Exception:
        try:
            await loc.click(force=True, timeout=1000, delay=opts.click_delay_ms, position={"x": max(1, pt.x - box.x), "y": max(1, pt.y - box.y)})
            return True
        except Exception:
            return False


async def _click_elem_tree(page: Page, elem: ElementHandle, cursor: Lateral, opts: Latitude) -> bool:
    cur = elem
    for _ in range(8):
        if not cur:
            break
        try:
            bd = await cur.bounding_box()
        except Exception:
            bd = None
        if bd:
            box = Box(**bd)
            if _is_turnstile_box(box):
                if await _click_box(page, box, cursor, opts):
                    return True
        try:
            parent = await cur.evaluate_handle("el => el.parentElement || (el.getRootNode() instanceof ShadowRoot ? el.getRootNode().host : null)")
            cur = parent.as_element() if parent else None
        except Exception:
            break
    return False


async def _click_turnstile(page: Page, cursor: Lateral, opts: Latitude) -> bool:
    for sel in ['iframe[src*="challenges.cloudflare.com"]', 'iframe[src*="cdn-cgi/challenge-platform"]']:
        loc = page.locator(sel)
        try:
            count = await loc.count()
        except Exception:
            continue
        for i in range(min(count, opts.max_candidates)):
            try:
                bd = await loc.nth(i).bounding_box(timeout=2000)
                if bd and bd["width"] > 0 and bd["height"] > 0:
                    box = Box(**bd)
                    if _is_turnstile_box(box):
                        pt = _click_pt(box)
                        await _prep_click(page, opts.foreground)
                        await page.mouse.click(pt.x, pt.y)
                        if opts.wait_after_click_ms > 0:
                            await page.wait_for_timeout(round(opts.wait_after_click_ms * (0.7 + random.random() * 0.6)))
                        return True
            except Exception:
                pass
    shuffled = list(opts.selectors)
    random.shuffle(shuffled)
    for sel in shuffled:
        if sel in _RESP_SEL:
            continue
        loc = page.locator(sel)
        try:
            count = await loc.count()
        except Exception:
            continue
        for i in range(min(count, opts.max_candidates)):
            target = loc.nth(i)
            if await _click_loc(page, target, cursor, opts):
                return True
            try:
                elem = await target.element_handle(timeout=1000)
                if elem:
                    try:
                        if await _click_elem_tree(page, elem, cursor, opts):
                            return True
                    finally:
                        await elem.dispose()
            except Exception:
                pass
    return False


async def _click_fallback(page: Page, cursor: Lateral, opts: Latitude) -> bool:
    candidates: List[Box] = []
    for sel in _FALLBACK:
        loc = page.locator(sel)
        try:
            count = min(await loc.count(), _FALL_LIMIT)
        except Exception:
            continue
        for i in range(count):
            try:
                bd = await loc.nth(i).bounding_box(timeout=250)
                if bd:
                    box = Box(**bd)
                    if _is_turnstile_box(box):
                        candidates.append(box)
            except Exception:
                pass
    candidates.sort(key=lambda b: abs(b.width - 300) + abs(b.height - 65))
    for box in candidates:
        if await _click_box(page, box, cursor, opts):
            return True
    return False


async def relate(page: Page, selectors: Optional[List[str]] = None) -> bool:
    sels = selectors or _TURNSTILE_SEL
    for sel in sels:
        loc = page.locator(sel)
        try:
            count = await loc.count()
        except Exception:
            continue
        if count == 0:
            continue
        if sel not in _RESP_SEL:
            return True
        for i in range(min(count, 5)):
            try:
                bd = await loc.nth(i).bounding_box(timeout=250)
                if bd and _is_turnstile_box(Box(**bd)):
                    return True
            except Exception:
                pass
    for sel in _FALLBACK:
        loc = page.locator(sel)
        try:
            count = min(await loc.count(), _FALL_LIMIT)
        except Exception:
            continue
        for i in range(count):
            try:
                bd = await loc.nth(i).bounding_box(timeout=250)
                if bd and _is_turnstile_box(Box(**bd)):
                    return True
            except Exception:
                pass
    return False


async def elate(page: Page, context: Optional[BrowserContext] = None, urls: Optional[List[str]] = None, min_token_len: int = _MIN_TOK) -> bool:
    ctx = context or page.context
    try:
        cookies = await ctx.cookies(urls or [])
        if any(c["name"] == "cf_clearance" for c in cookies):
            return True
    except Exception:
        pass
    try:
        state = await page.evaluate("""(minLen) => {
            const inputs = document.querySelectorAll('[name="cf-turnstile-response"], [name="turnstile-response"], [data-cf-turnstile-response]');
            let tokenFound = false;
            for (const el of inputs) {
                const val = el.value || el.getAttribute('data-cf-turnstile-response') || '';
                if (val.trim().length >= minLen) { tokenFound = true; break; }
            }
            const present = document.querySelectorAll('.cf-turnstile, iframe[src*="challenges.cloudflare.com"]').length > 0;
            return { tokenFound, present };
        }""", min_token_len)
        if state.get("present") and not state.get("tokenFound"):
            return False
        return bool(state.get("tokenFound"))
    except Exception:
        return False


async def translate(page: Page) -> bool:
    return await _is_managed(page)


async def collate(page: Page, context: Optional[BrowserContext] = None, urls: Optional[List[str]] = None, min_token_len: int = _MIN_TOK, timeout_ms: int = 7000) -> CFData:
    ctx = context or page.context
    solved = await elate(page, ctx, urls, min_token_len)
    while not solved:
        await page.wait_for_timeout(500)
        solved = await elate(page, ctx, urls, min_token_len)
    start = time.time()
    has_clearance = False
    while time.time() - start < timeout_ms / 1000:
        try:
            cookies = await ctx.cookies(urls or [])
            if any(c["name"] == "cf_clearance" for c in cookies):
                has_clearance = True
                break
        except Exception:
            pass
        await page.wait_for_timeout(500)
    try:
        raw = await page.evaluate("""({ responseSelectors, cfFieldSel, minTokenLen }) => {
            const responseData = [];
            const widgets = [];
            const fields = [];
            const iframeSrcs = [];
            const scriptSrcs = [];
            const sitekeys = [];
            const rayIds = [];
            const pushUnique = (arr, val) => { if (val && !arr.includes(val)) arr.push(val); };
            const valueFor = (el) => {
                if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return el.value;
                return el.getAttribute('value') || el.getAttribute('data-cf-turnstile-response') || el.getAttribute('data-turnstile-response') || el.getAttribute('data-turnstile-token') || '';
            };
            for (const sel of responseSelectors) {
                try { document.querySelectorAll(sel).forEach(el => {
                    const v = valueFor(el).trim();
                    if (v) { const src = el.hasAttribute('data-cf-turnstile-response') || el.hasAttribute('data-turnstile-response') || el.hasAttribute('data-turnstile-token') ? 'attribute' : 'field'; if (!responseData.some(r => r.value === v)) responseData.push({ source: src, value: v }); }
                }); } catch(e) {}
            }
            document.querySelectorAll('[data-sitekey], .cf-turnstile').forEach(el => {
                const sk = el.getAttribute('data-sitekey') || undefined;
                widgets.push({ sitekey: sk, action: el.getAttribute('data-action') || undefined, cData: el.getAttribute('data-cdata') || undefined, callback: el.getAttribute('data-callback') || undefined, theme: el.getAttribute('data-theme') || undefined, size: el.getAttribute('data-size') || undefined, language: el.getAttribute('data-language') || undefined });
                pushUnique(sitekeys, sk);
            });
            document.querySelectorAll('iframe').forEach(iframe => {
                const src = iframe.getAttribute('src');
                if (!src || !/cloudflare|turnstile|challenge/i.test(src)) return;
                pushUnique(iframeSrcs, src);
                try { const u = new URL(src, location.href); pushUnique(sitekeys, u.searchParams.get('sitekey')); pushUnique(sitekeys, u.searchParams.get('siteKey')); pushUnique(sitekeys, u.searchParams.get('k')); } catch(e) {}
            });
            document.querySelectorAll('script[src]').forEach(s => { const src = s.getAttribute('src'); if (src && /cloudflare|turnstile|challenge-platform/i.test(src)) pushUnique(scriptSrcs, src); });
            try { document.querySelectorAll(cfFieldSel).forEach(el => {
                const v = valueFor(el).trim(); const n = el.getAttribute('name') || undefined;
                const rid = el.getAttribute('data-ray') || el.getAttribute('data-cf-ray');
                pushUnique(rayIds, rid); if (v) fields.push({ name: n, value: v });
            }); } catch(e) {}
            const collectStorage = (st) => { const entries = []; for (let i = 0; i < st.length; i++) { const k = st.key(i); if (k && /cloudflare|turnstile|cf[_-]|cfchl|cf_chl|challenge/i.test(k)) entries.push({ key: k, value: st.getItem(k) || '' }); } return entries; };
            const safeSt = (fn) => { try { return collectStorage(fn()); } catch(e) { return []; } };
            const safeCookieNames = () => { try { return document.cookie.split(';').map(p => p.trim().split('=')[0]).filter(Boolean); } catch(e) { return []; } };
            const tokens = responseData.map(r => r.value).filter(v => v.length >= minTokenLen);
            const present = responseData.length > 0 || widgets.length > 0 || sitekeys.length > 0 || iframeSrcs.some(s => /turnstile/i.test(s));
            const mText = (document.title || '') + '\\n' + (document.body?.innerText?.slice(0, 5000) || '') + '\\n' + location.href;
            const managed = /just a moment|security verification|checking your browser/i.test(mText) && /cloudflare|verify you are not a bot|malicious bots|ray id/i.test(mText);
            return {
                url: location.href, userAgent: navigator.userAgent, documentCookieNames: safeCookieNames(),
                turnstile: { present, solved: tokens.length > 0, responses: responseData, tokens: [...new Set(tokens)], sitekeys: [...new Set(sitekeys)], widgets, iframes: [...new Set(iframeSrcs)], scripts: [...new Set(scriptSrcs)] },
                challenge: { managed, fields, rayIds: [...new Set(rayIds)] },
                storage: { local: safeSt(() => localStorage), session: safeSt(() => sessionStorage) }
            };
        }""", {"responseSelectors": _RESP_SEL, "cfFieldSel": _CF_FIELD, "minTokenLen": min_token_len})
    except Exception:
        raw = {}
    cookies_raw = []
    try:
        cookies_raw = await ctx.cookies(urls or [])
    except Exception:
        pass
    cf_cookies = [CFCookie(name=c["name"], value=c["value"], domain=c.get("domain"), path=c.get("path"), expires=c.get("expires")) for c in cookies_raw if re.match(r"^(?:__cf|_cf|cf_)", c["name"], re.IGNORECASE)]
    all_cookies = [CFCookie(name=c["name"], value=c["value"], domain=c.get("domain"), path=c.get("path"), expires=c.get("expires")) for c in cookies_raw]
    clearance_val = ""
    for c in cookies_raw:
        if c["name"] == "cf_clearance":
            clearance_val = c["value"]
            break
    ts = raw.get("turnstile", {})
    ch = raw.get("challenge", {})
    st = raw.get("storage", {})
    return CFData(
        url=raw.get("url", ""),
        user_agent=raw.get("userAgent", ""),
        document_cookie_names=raw.get("documentCookieNames", []),
        cookies=all_cookies,
        cf_cookies=cf_cookies,
        clearance=clearance_val,
        cf_clearance=clearance_val,
        turnstile_present=ts.get("present", False),
        turnstile_solved=ts.get("solved", False),
        turnstile_tokens=ts.get("tokens", []),
        turnstile_responses=[TurnstileResp(source=r.get("source", ""), value=r.get("value", "")) for r in ts.get("responses", [])],
        turnstile_sitekeys=ts.get("sitekeys", []),
        turnstile_widgets=[TurnstileWidget(**w) for w in ts.get("widgets", [])],
        turnstile_iframes=ts.get("iframes", []),
        turnstile_scripts=ts.get("scripts", []),
        challenge_cleared=has_clearance,
        challenge_managed=ch.get("managed", False),
        challenge_fields=[CFField(name=f.get("name"), value=f.get("value", "")) for f in ch.get("fields", [])],
        challenge_ray_ids=ch.get("rayIds", []),
        storage_local=[StorageEntry(key=e.get("key", ""), value=e.get("value", "")) for e in st.get("local", [])],
        storage_session=[StorageEntry(key=e.get("key", ""), value=e.get("value", "")) for e in st.get("session", [])],
    )


async def _click_managed(page: Page, cursor: Lateral, opts: Latitude) -> bool:
    try:
        for sel in ['iframe[src*="challenges.cloudflare.com"]', 'iframe[src*="cdn-cgi/challenge-platform"]']:
            loc = page.locator(sel)
            if await loc.count() > 0:
                try:
                    bd = await loc.first.bounding_box(timeout=3000)
                    if bd and bd["width"] > 0 and bd["height"] > 0:
                        x = bd["x"] + 28 + (random.random() - 0.5) * 8
                        y = bd["y"] + bd["height"] / 2 + (random.random() - 0.5) * 6
                        await _prep_click(page, opts.foreground)
                        await page.mouse.click(x, y)
                        if opts.wait_after_click_ms > 0:
                            await page.wait_for_timeout(round(opts.wait_after_click_ms * (0.7 + random.random() * 0.6)))
                        return True
                except Exception:
                    pass
    except Exception:
        pass
    try:
        checkbox = page.locator('input[type="checkbox"]')
        if await checkbox.count() > 0:
            if await _click_loc(page, checkbox.first, cursor, opts):
                return True
    except Exception:
        pass
    try:
        btn = page.locator('button:has-text("Verify"), button:has-text("验证"), input[type="submit"]')
        if await btn.count() > 0:
            if await _click_loc(page, btn.first, cursor, opts):
                return True
    except Exception:
        pass
    if await _click_turnstile(page, cursor, opts):
        return True
    if await _click_fallback(page, cursor, opts):
        return True
    return False


async def slate_once(page: Page, cursor: Lateral, opts: Latitude) -> dict:
    if await elate(page):
        return {"engaged": False, "status": "solved"}
    managed = await _is_managed(page)
    if managed:
        return {"engaged": False, "status": "managed-challenge"}
    if await _click_turnstile(page, cursor, opts):
        return {"engaged": True, "status": "engaged"}
    if await _click_fallback(page, cursor, opts):
        return {"engaged": True, "status": "engaged"}
    return {"engaged": False, "status": "not-found"}


class Slate:
    def __init__(self, page: Page, opts: Optional[Latitude] = None):
        self._page = page
        self._opts = opts or Latitude()
        self._cursor = Lateral(page)
        self._closed = False
        self._running = False
        self._pending = False
        self._attempts = 0
        self._next_click_at = 0.0
        self._task: Optional[asyncio.Task] = None
        self._last_managed_log = 0.0
        self._managed_since: Optional[float] = None
        self._managed_waiting = False

    async def _run(self):
        if self._closed:
            return
        if self._running:
            self._pending = True
            return
        self._running = True
        self._pending = False
        try:
            now = time.time() * 1000
            if now < self._next_click_at:
                return
            if self._managed_waiting:
                return
            result = await slate_once(self._page, self._cursor, self._opts)
            if result["status"] == "managed-challenge":
                if self._managed_since is None:
                    self._managed_since = time.time() * 1000
                    self._managed_waiting = True
                    self._opts.logger and self._opts.logger("cloudflare managed challenge detected; waiting for auto-resolve")
                self._next_click_at = time.time() * 1000 + 5000
                return
            if result["status"] in ("solved", "not-found"):
                self._attempts = 0
                self._next_click_at = 0
                self._managed_since = None
                self._managed_waiting = False
                return
            if result["engaged"]:
                self._attempts += 1
                cd = min(self._opts.max_click_cooldown_ms, self._opts.click_cooldown_ms * min(self._attempts, 6))
                self._next_click_at = time.time() * 1000 + cd
                self._opts.logger and self._opts.logger(f"turnstile engaged; cooldown {cd}ms")
        except Exception as e:
            self._opts.logger and self._opts.logger(str(e))
        finally:
            self._running = False
            if self._pending and not self._closed:
                self._schedule()

    def _schedule(self):
        if self._closed or (self._task and not self._task.done()):
            return
        self._task = asyncio.ensure_future(self._run())

    def tick(self):
        self._schedule()

    async def start(self):
        self.tick()
        self._page.on("close", self.stop)
        self._page.on("framenavigated", lambda: self.tick())
        while not self._closed:
            await asyncio.sleep(self._opts.interval_ms / 1000)
            if self._managed_waiting:
                elapsed = (time.time() * 1000 - self._managed_since) if self._managed_since else 0
                if elapsed > self._opts.managed_timeout_ms:
                    self._managed_waiting = False
                    self._managed_since = None
                    self._opts.logger and self._opts.logger("managed challenge timeout; attempting interaction")
                    if await _click_managed(self._page, self._cursor, self._opts):
                        self._next_click_at = time.time() * 1000 + self._opts.click_cooldown_ms
                    else:
                        try:
                            await self._page.reload(timeout=15000)
                        except Exception:
                            pass
                        self._next_click_at = time.time() * 1000 + 3000
                else:
                    cookies = []
                    try:
                        cookies = await self._page.context.cookies()
                    except Exception:
                        pass
                    if any(c["name"] == "cf_clearance" for c in cookies):
                        self._managed_waiting = False
                        self._managed_since = None
                        self._opts.logger and self._opts.logger("managed challenge auto-resolved")
                    else:
                        for sel in ['iframe[src*="challenges.cloudflare.com"]', 'iframe[src*="cdn-cgi/challenge-platform"]']:
                            try:
                                loc = self._page.locator(sel)
                                if await loc.count() > 0:
                                    bd = await loc.first.bounding_box(timeout=2000)
                                    if bd and bd["width"] > 0 and bd["height"] > 0:
                                        box = Box(**bd)
                                        if _is_turnstile_box(box):
                                            pt = _click_pt(box)
                                            await self._page.mouse.click(pt.x, pt.y)
                                            self._opts.logger and self._opts.logger("turnstile widget engaged during managed wait")
                                            await self._page.wait_for_timeout(round(self._opts.wait_after_click_ms * (0.7 + random.random() * 0.6)))
                                            break
                            except Exception:
                                pass
            self.tick()

    def stop(self):
        self._closed = True
        if self._task and not self._task.done():
            self._task.cancel()


class ContextSlate:
    def __init__(self, context: BrowserContext, opts: Optional[Latitude] = None):
        self._context = context
        self._opts = opts or Latitude()
        self._watchers: Dict[Page, Slate] = {}
        self._closed = False

    async def _attach(self, page: Page):
        if page in self._watchers or self._closed:
            return
        w = Slate(page, self._opts)
        self._watchers[page] = w
        page.on("close", lambda: self._detach(page))
        asyncio.ensure_future(w.start())

    def _detach(self, page: Page):
        w = self._watchers.pop(page, None)
        if w:
            w.stop()

    async def install(self):
        for page in self._context.pages:
            await self._attach(page)
        self._context.on("page", lambda p: asyncio.ensure_future(self._attach(p)))

    def uninstall(self):
        self._closed = True
        for w in self._watchers.values():
            w.stop()
        self._watchers.clear()
