# latcf / cursor

import math
import random
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from patchright.async_api import Page, CDPSession


@dataclass
class Point:
    x: float
    y: float


@dataclass
class TimedVector:
    x: float
    y: float
    timestamp: float


@dataclass
class Box:
    x: float
    y: float
    width: float
    height: float


_OVERSHOOT = 500
_JITTER = 1.5
_WIND = 0.25


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _dist(a: Point, b: Point) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def _add(a: Point, b: Point) -> Point:
    return Point(a.x + b.x, a.y + b.y)


def _sub(a: Point, b: Point) -> Point:
    return Point(a.x - b.x, a.y - b.y)


def _mul(a: Point, s: float) -> Point:
    return Point(a.x * s, a.y * s)


def _mag(a: Point) -> float:
    return math.hypot(a.x, a.y)


def _unit(a: Point) -> Point:
    m = _mag(a)
    return Point(a.x / m, a.y / m) if m != 0 else Point(0, 0)


def _perp(a: Point) -> Point:
    return Point(-a.y, a.x)


def _gauss(mean: float = 0, std: float = 1) -> float:
    u = random.random()
    while u == 0:
        u = random.random()
    v = random.random()
    while v == 0:
        v = random.random()
    return mean + std * math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def _gauss_clamp(mean: float, std: float, lo: float, hi: float) -> float:
    return _clamp(_gauss(mean, std), lo, hi)


def _rand(lo: float, hi: float) -> float:
    return lo + random.random() * (hi - lo)


def _ease_io(t: float) -> float:
    return (1 - math.cos(math.pi * t)) / 2


def _inv_ease_io(y: float) -> float:
    return math.acos(1 - 2 * _clamp(y, 0, 1)) / math.pi


def _fitts(distance: float, target_w: float, speed: float) -> float:
    b = 150
    idx = math.log2(distance / target_w + 1)
    base = (b * idx) / max(0.01, speed)
    return max(50, base * (1 + _gauss(0, 0.05)))


def _bezier(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1 - t
    return Point(
        u**3 * p0.x + 3 * u**2 * t * p1.x + 3 * u * t**2 * p2.x + t**3 * p3.x,
        u**3 * p0.y + 3 * u**2 * t * p1.y + 3 * u * t**2 * p2.y + t**3 * p3.y,
    )


def _ctrl_pts(start: Point, end: Point) -> Tuple[Point, Point]:
    length = _dist(start, end)
    d = _sub(end, start)
    spread = _clamp(length * 0.35, 5, 220)
    pd = _perp(_unit(d))
    s1 = 1 if random.random() < 0.5 else -1
    s2 = -s1 if random.random() < 0.35 else s1
    t1 = _rand(0.15, 0.45)
    t2 = _rand(0.55, 0.85)
    o1 = spread * _rand(0.2, 1.0) * s1
    o2 = spread * _rand(0.2, 0.9) * s2
    return (
        _add(_add(start, _mul(d, t1)), _mul(pd, o1)),
        _add(_add(start, _mul(d, t2)), _mul(pd, o2)),
    )


def _tremor(pts: list, amp: float) -> list:
    if amp <= 0 or len(pts) < 3:
        return pts
    out = []
    for i, p in enumerate(pts):
        if i == len(pts) - 1:
            out.append(p)
            continue
        prev = pts[max(0, i - 1)]
        nxt = pts[min(len(pts) - 1, i + 1)]
        d = _unit(_sub(nxt, prev))
        pd = _perp(d)
        np_ = _gauss(0, amp)
        na = _gauss(0, amp * 0.25)
        out.append(Point(p.x + pd.x * np_ + d.x * na, p.y + pd.y * np_ + d.y * na))
    return out


def _wind_drift(pts: list, strength: float) -> list:
    if strength <= 0 or len(pts) < 3:
        return pts
    n = len(pts)
    res = list(pts)
    wx = wy = 0.0
    cap = strength * 10
    for i in range(1, n - 1):
        prog = i / (n - 1)
        decay = 1 - prog**1.5
        wx += _gauss(0, strength * 0.6)
        wy += _gauss(0, strength * 0.6)
        wm = math.hypot(wx, wy)
        if wm > cap:
            wx, wy = wx / wm * cap, wy / wm * cap
        res[i] = Point(res[i].x + wx * decay, res[i].y + wy * decay)
    return res


def _spatial(start: Point, end: Point, jitter: float = _JITTER, wind: float = _WIND, speed: float = 1.0) -> list:
    length = _dist(start, end)
    if length < 1:
        return [Point(end.x, end.y)]
    total_ms = _fitts(length, 80, speed)
    sv = 1 + _gauss(0, 0.08)
    steps = _clamp(math.ceil(total_ms * sv / 8), 8, 250)
    c1, c2 = _ctrl_pts(start, end)
    raw = [_bezier(start, c1, c2, end, i / steps) for i in range(1, steps + 1)]
    raw[-1] = Point(end.x, end.y)
    w = _wind_drift(raw, wind)
    n = _tremor(w, jitter)
    n[-1] = Point(end.x, end.y)
    return n


def _stamp(pts: list, total_ms: float) -> list:
    n = len(pts)
    if n == 0:
        return []
    now = time.time() * 1000
    if n == 1:
        return [TimedVector(pts[0].x, pts[0].y, now)]
    pause_count = 0 if random.random() < 0.4 else (1 if random.random() < 0.7 else 2)
    pauses = set()
    for _ in range(pause_count):
        pauses.add(int(_rand(n * 0.2, n * 0.8)))
    acc = 0
    out = []
    for i, pt in enumerate(pts):
        sf = i / (n - 1)
        tf = _inv_ease_io(sf)
        ts = now + round(tf * total_ms)
        if i in pauses:
            acc += round(_rand(8, 35))
        ts += acc
        out.append(TimedVector(pt.x, pt.y, ts))
    return out


def _micro_correct(current: Point, target: Point) -> Tuple[list, float]:
    d = _dist(current, target)
    if d < 0.5:
        return [Point(target.x, target.y)], 15
    of = _rand(0.06, 0.22)
    over = _add(target, _mul(_sub(target, current), of))
    pts = [
        Point(over.x + _gauss(0, 0.8), over.y + _gauss(0, 0.8)),
        Point(target.x + _gauss(0, 0.4), target.y + _gauss(0, 0.4)),
        Point(target.x, target.y),
    ]
    return pts, _clamp(d * 2, 20, 80)


def _overshoot(start: Point, end: Point) -> Point:
    length = _dist(start, end)
    if length < 1:
        return end
    d = _unit(_sub(end, start))
    pd = _perp(d)
    od = _rand(8, min(60, length * 0.08))
    lat = _gauss(0, 6)
    return Point(end.x + d.x * od + pd.x * lat, end.y + d.y * od + pd.y * lat)


def _idle_jitter(center: Point, duration_ms: float, amp: float = 1.2) -> list:
    if duration_ms <= 0:
        return []
    hz = 15
    count = max(2, int(duration_ms / 1000 * hz))
    interval = duration_ms / count
    now = time.time() * 1000
    out = []
    for i in range(count):
        out.append(TimedVector(center.x + _gauss(0, amp), center.y + _gauss(0, amp), now + i * interval))
    out.append(TimedVector(center.x, center.y, now + duration_ms))
    return out


class Lateral:
    def __init__(self, page: Page, start: Optional[Point] = None):
        self._page = page
        self._loc = start or Point(round(100 + random.random() * 400), round(80 + random.random() * 300))
        self._cdp: Optional[CDPSession] = None

    async def _get_cdp(self) -> CDPSession:
        if self._cdp is None:
            self._cdp = await self._page.context.new_cdp_session(self._page)
        return self._cdp

    async def _wait(self, ms: float):
        if ms and ms > 0:
            await self._page.wait_for_timeout(ms)

    async def _dispatch(self, path: list):
        if not path:
            return
        cdp = await self._get_cdp()
        base = path[0].timestamp
        start = time.time() * 1000
        for pt in path:
            if self._page.is_closed():
                return
            scheduled = pt.timestamp - base
            elapsed = time.time() * 1000 - start
            delay = scheduled - elapsed
            if delay > 0:
                await self._wait(delay)
            try:
                ts_j = _gauss(0, 0.002)
                await cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved",
                    "x": pt.x,
                    "y": pt.y,
                    "timestamp": pt.timestamp / 1000 + ts_j,
                })
            except Exception:
                if not self._page.is_closed():
                    raise
                return

    async def _move_direct(self, dest: Point, speed: float = 1.0, jitter: float = _JITTER, wind: float = _WIND, micro: bool = True):
        length = _dist(self._loc, dest)
        if length < 0.5:
            self._loc = Point(dest.x, dest.y)
            return
        total_ms = _fitts(length, 80, speed)
        spatial = _spatial(self._loc, dest, jitter, wind, speed)
        timed = _stamp(spatial, total_ms)
        if micro and length > 5:
            last = timed[-1]
            corr_pts, corr_ms = _micro_correct(Point(last.x, last.y), dest)
            base = last.timestamp
            corr_timed = [
                TimedVector(p.x, p.y, base + round((i + 1) / len(corr_pts) * corr_ms))
                for i, p in enumerate(corr_pts)
            ]
            await self._dispatch(timed[:-1] + corr_timed)
        else:
            await self._dispatch(timed)
        self._loc = Point(dest.x, dest.y)

    async def move_to(self, dest: Point, speed: float = 1.0, jitter: float = _JITTER, wind: float = _WIND, overshoot_threshold: float = _OVERSHOOT, move_delay: float = 0, random_delay: bool = True):
        if _dist(self._loc, dest) > overshoot_threshold:
            over = _overshoot(self._loc, dest)
            await self._move_direct(over, speed=speed * 1.3, micro=False)
        await self._move_direct(dest, speed=speed, jitter=jitter, wind=wind)
        d = move_delay * random.random() if random_delay else move_delay
        await self._wait(d)

    async def click(self, target: Point, button: str = "left", click_count: int = 1, speed: float = 1.0, hesitate: float = 0, hold_ms: Optional[float] = None, overshoot_threshold: float = 420):
        await self.move_to(target, speed=speed, overshoot_threshold=overshoot_threshold)
        if hesitate > 0:
            jpath = _idle_jitter(self._loc, hesitate, 0.9)
            await self._dispatch(jpath)
        cdp = await self._get_cdp()
        for idx in range(1, max(1, click_count) + 1):
            sx = self._loc.x + _gauss(0, 0.3)
            sy = self._loc.y + _gauss(0, 0.3)
            ts_j = _gauss(0, 0.0015)
            await cdp.send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": sx, "y": sy,
                "button": button,
                "clickCount": idx,
                "timestamp": time.time() + ts_j,
            })
            hold = hold_ms if hold_ms is not None else round(_gauss_clamp(85, 20, 45, 140))
            await self._wait(hold)
            await cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": sx, "y": sy,
                "button": button,
                "clickCount": idx,
                "timestamp": time.time() + ts_j,
            })
            if idx < click_count:
                inter = hold_ms if hold_ms is not None else round(_gauss_clamp(70, 15, 35, 110))
                await self._wait(inter)

    async def double_click(self, target: Point, button: str = "left", speed: float = 1.0):
        await self.move_to(target, speed=speed)
        cdp = await self._get_cdp()
        sx = self._loc.x + _gauss(0, 0.3)
        sy = self._loc.y + _gauss(0, 0.3)
        await cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": sx, "y": sy, "button": button, "clickCount": 1, "timestamp": time.time()})
        await self._wait(round(_rand(55, 90)))
        await cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": sx, "y": sy, "button": button, "clickCount": 1, "timestamp": time.time()})
        await self._wait(round(_rand(90, 200)))
        drift = Point(self._loc.x + _gauss(0, 1.2), self._loc.y + _gauss(0, 1.2))
        await self._move_direct(drift, speed=4, micro=False, jitter=0, wind=0)
        sx2 = self._loc.x + _gauss(0, 0.3)
        sy2 = self._loc.y + _gauss(0, 0.3)
        await cdp.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": sx2, "y": sy2, "button": button, "clickCount": 2, "timestamp": time.time()})
        await self._wait(round(_rand(55, 90)))
        await cdp.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": sx2, "y": sy2, "button": button, "clickCount": 2, "timestamp": time.time()})

    async def scroll(self, target: Point, delta_x: float = 0, delta_y: float = 300, steps: int = 6, step_delay: float = 60):
        await self.move_to(target)
        steps = _clamp(steps, 1, 50)
        cdp = await self._get_cdp()
        for i in range(steps):
            delay = step_delay + _gauss(0, step_delay * 0.2)
            await self._wait(delay)
            try:
                await cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseWheel",
                    "x": self._loc.x, "y": self._loc.y,
                    "deltaX": delta_x / steps,
                    "deltaY": delta_y / steps,
                    "timestamp": time.time(),
                })
            except Exception:
                if not self._page.is_closed():
                    raise
                return

    async def hover(self, target: Point, duration: float = 500, jitter: float = _JITTER, speed: float = 1.0):
        await self.move_to(target, speed=speed)
        jpath = _idle_jitter(target, duration, jitter)
        await self._dispatch(jpath)

    @property
    def location(self) -> Point:
        return Point(self._loc.x, self._loc.y)
