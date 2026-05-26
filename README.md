<div align="center">

<img width="0" height="0" style="margin:0; padding:0;" />

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12&height=180&section=header&text=CloudFlare%20Challenger&fontSize=36&fontColor=fff&animation=twinkling&fontAlignY=32&desc=Turnstile%20Auto-Solver%20%7C%20Human-Like%20Cursor&descSize=16&descAlignY=52" alt="header" />

<br/>

[![PyPI](https://img.shields.io/pypi/v/latcf?color=FF6B9D&style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/latcf/)
[![Python](https://img.shields.io/pypi/pyversions/latcf?color=9D6BFF&style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/latcf/)
[![License](https://img.shields.io/github/license/LATstudio-WeFun/lat-cf-challenger?color=6BFF9D&style=for-the-badge)](https://github.com/LATstudio-WeFun/lat-cf-challenger)

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/jEaY4etBTY)
[![QQ](https://img.shields.io/badge/QQ-Group-12B7F5?style=for-the-badge&logo=tencent-qq&logoColor=white)](https://qm.qq.com/q/cqtKjQPRMA)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/LATstudio-WeFun/lat-cf-challenger)

</div>

---

<details open>
<summary>🇬🇧 English</summary>

### Install

```
pip install latcf
```

Chromium is installed automatically on first use.

### Quick Start

```python
import asyncio
from latcf import latch

async def main():
    cf = await latch(headless=False, turnstile=True)
    page = await cf.new_page()
    await page.goto("https://example.com")
    await cf.close()

asyncio.run(main())
```

`turnstile=True` — detection, clicking, retrying, all automatic.

### API

| Function | Description |
|----------|-------------|
| `latch()` | Launch browser with turnstile auto-solve |
| `latch_context()` | Launch persistent context with turnstile auto-solve |
| `relate(page)` | Is there a turnstile on this page? |
| `elate(page)` | Has the turnstile been solved? |
| `translate(page)` | Is this a "Just a moment..." page? |
| `collate(page)` | Grab all cloudflare data (cookies, tokens, etc) |
| `plate()` | Generate a real-looking user agent |
| `plate_context(opts)` | Patch your options dict with a real UA |

### Browser Launch

```python
from latcf import latch, latch_context

cf = await latch(headless=False, turnstile=True)
page = await cf.new_page()

cf = await latch(headless=False, channel="chrome", turnstile=True)

ctx = await latch_context("./profile", headless=False, turnstile=True)

cf = await latch(headless=False, turnstile=False)

await cf.close()
```

### Solver Settings

Defaults work for most cases. Tweak if needed:

```python
from latcf import latch, Latitude

opts = Latitude(
    timeout_ms=3000,
    interval_ms=500,
    foreground=True,
    click_delay_ms=35,
    mouse_move_steps=8,
    wait_after_click_ms=100,
    click_cooldown_ms=5000,
    max_click_cooldown_ms=45000,
    logger=print,
)

cf = await latch(headless=False, turnstile=opts)
```

The solver watches navigations, DOM changes, page reloads. Before clicking it wanders nearby, pauses like a human, approaches from a random angle. Managed challenge pages are detected and skipped.

### Human-Like Cursor

`Lateral` moves along bezier curves with hand tremor, wind drift, micro-corrections, and overshoot. Click timing uses gaussian distribution.

```python
from latcf import Lateral, Point

cursor = Lateral(page)

await cursor.move_to(Point(640, 360))
await cursor.click(Point(100, 200))
await cursor.double_click(Point(300, 400))
await cursor.scroll(Point(300, 400), delta_y=600, steps=8)
await cursor.hover(Point(300, 400), duration=800)
```

| Action | Options |
|--------|---------|
| move | `speed` (1.0), `jitter` (1.5), `wind` (0.25), `overshoot_threshold` (500) |
| click | `button` ("left"), `click_count` (1), `hesitate` (0), `hold_ms` (~85) |
| scroll | `delta_x` (0), `delta_y` (300), `steps` (6), `step_delay` (60) |
| hover | `duration` (500), `jitter` (1.5) |

### Cloudflare Checks

```python
from latcf import relate, elate, translate, collate

found = await relate(page)       # turnstile present?
solved = await elate(page)       # already solved?
managed = await translate(page)  # managed challenge page?
data = await collate(page)       # get everything
```

`collate()` returns a `CFData` object: `cf_clearance`, `turnstile_tokens`, `turnstile_sitekeys`, `cf_cookies`, `challenge_managed`, `challenge_cleared`, `storage_local`, `storage_session`, etc.

### Headless UA Patch

Headless chrome leaks `HeadlessChrome` in the UA. latcf replaces it automatically.

```python
from latcf import plate
ua = plate(channel="chrome")
```

Env: `LAT_CF_HEADLESS_UA=0` to disable, `LAT_CF_HEADLESS_UA=<string>` for custom.

### Use as API

latcf works as a backend for your own API. FastAPI example:

```python
from fastapi import FastAPI
from latcf import latch, collate

app = FastAPI()

@app.get("/solve")
async def solve(url: str):
    cf = await latch(headless=True, turnstile=True)
    page = await cf.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    data = await collate(page, timeout_ms=15000)
    await cf.close()
    return {
        "solved": data.turnstile_solved,
        "clearance": data.cf_clearance,
        "tokens": data.turnstile_tokens,
    }
```

`uvicorn main:app --host 0.0.0.0 --port 8000` then `GET /solve?url=https://example.com`.

### Requirements

- Python >= 3.8
- patchright >= 1.0.0

</details>

---

<details>
<summary>🇨🇳 中文</summary>

### 安装

```
pip install latcf
```

Chromium 会在首次使用时自动安装。

### 快速上手

```python
import asyncio
from latcf import latch

async def main():
    cf = await latch(headless=False, turnstile=True)
    page = await cf.new_page()
    await page.goto("https://example.com")
    await cf.close()

asyncio.run(main())
```

`turnstile=True` — 检测、点击、重试，全自动。

### API

| 函数 | 作用 |
|------|------|
| `latch()` | 启动浏览器，自动解决 Turnstile |
| `latch_context()` | 启动持久化上下文，自动解决 Turnstile |
| `relate(page)` | 页面上有没有 Turnstile？ |
| `elate(page)` | Turnstile 解决了没？ |
| `translate(page)` | 是不是 "Just a moment..." 页面？ |
| `collate(page)` | 拿到所有 Cloudflare 数据（cookie、token 等） |
| `plate()` | 生成一个看起来真实的 UA |
| `plate_context(opts)` | 给你的配置加上真实 UA |

### 启动浏览器

```python
from latcf import latch, latch_context

cf = await latch(headless=False, turnstile=True)
page = await cf.new_page()

cf = await latch(headless=False, channel="chrome", turnstile=True)

ctx = await latch_context("./profile", headless=False, turnstile=True)

cf = await latch(headless=False, turnstile=False)

await cf.close()
```

### 解决器配置

默认配置大多数情况够用，想调的话：

```python
from latcf import latch, Latitude

opts = Latitude(
    timeout_ms=3000,
    interval_ms=500,
    foreground=True,
    click_delay_ms=35,
    mouse_move_steps=8,
    wait_after_click_ms=100,
    click_cooldown_ms=5000,
    max_click_cooldown_ms=45000,
    logger=print,
)

cf = await latch(headless=False, turnstile=opts)
```

解决器自动监听页面导航、DOM 变化、页面重载。点击前会在附近随机游荡、像人一样停顿，然后从随机角度接近。托管挑战页面自动识别并跳过。

### 仿人类鼠标

`Lateral` 沿贝塞尔曲线移动，带手抖、风漂移、到达微修正、长距离过冲。点击时间用高斯分布。

```python
from latcf import Lateral, Point

cursor = Lateral(page)

await cursor.move_to(Point(640, 360))
await cursor.click(Point(100, 200))
await cursor.double_click(Point(300, 400))
await cursor.scroll(Point(300, 400), delta_y=600, steps=8)
await cursor.hover(Point(300, 400), duration=800)
```

| 操作 | 参数 |
|------|------|
| 移动 | `speed` (1.0)、`jitter` (1.5)、`wind` (0.25)、`overshoot_threshold` (500) |
| 点击 | `button` ("left")、`click_count` (1)、`hesitate` (0)、`hold_ms` (~85) |
| 滚动 | `delta_x` (0)、`delta_y` (300)、`steps` (6)、`step_delay` (60) |
| 悬停 | `duration` (500)、`jitter` (1.5) |

### Cloudflare 检查

```python
from latcf import relate, elate, translate, collate

found = await relate(page)       # 有没有 Turnstile？
solved = await elate(page)       # 解决了没？
managed = await translate(page)  # 是托管挑战页面吗？
data = await collate(page)       # 拿全部数据
```

`collate()` 返回 `CFData` 对象：`cf_clearance`、`turnstile_tokens`、`turnstile_sitekeys`、`cf_cookies`、`challenge_managed`、`challenge_cleared`、`storage_local`、`storage_session` 等。

### Headless UA 修补

Headless 模式的 UA 带 `HeadlessChrome`，一秒被识别。latcf 自动替换成真实 Chrome UA。

```python
from latcf import plate
ua = plate(channel="chrome")
```

环境变量：`LAT_CF_HEADLESS_UA=0` 禁用，`LAT_CF_HEADLESS_UA=<字符串>` 用自定义的。

### 作为 API 使用

latcf 可以直接作为后端 API 使用。FastAPI 示例：

```python
from fastapi import FastAPI
from latcf import latch, collate

app = FastAPI()

@app.get("/solve")
async def solve(url: str):
    cf = await latch(headless=True, turnstile=True)
    page = await cf.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    data = await collate(page, timeout_ms=15000)
    await cf.close()
    return {
        "solved": data.turnstile_solved,
        "clearance": data.cf_clearance,
        "tokens": data.turnstile_tokens,
    }
```

`uvicorn main:app --host 0.0.0.0 --port 8000` 启动，然后 `GET /solve?url=https://example.com` 调用。

### 依赖

- Python >= 3.8
- patchright >= 1.0.0

</details>

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12&height=100&section=footer" alt="footer" />

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/jEaY4etBTY)
[![QQ](https://img.shields.io/badge/QQ-Group-12B7F5?style=for-the-badge&logo=tencent-qq&logoColor=white)](https://qm.qq.com/q/cqtKjQPRMA)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/LATstudio-WeFun/lat-cf-challenger)

MIT License / Made by ilat

</div>
