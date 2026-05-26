<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,12&height=220&section=header&text=latcf&fontSize=48&fontColor=fff&animation=twinkling&fontAlignY=30&desc=Cloudflare%20Challenger%20%20%7C%20%20Turnstile%20%20%7C%20%20Managed%20Challenge&descSize=15&descAlignY=52&descColor=dde" alt="header" />

<br/>

[![PyPI](https://img.shields.io/pypi/v/latcf?color=4A90D9&style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/latcf/)
[![Python](https://img.shields.io/pypi/pyversions/latcf?color=306998&style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/latcf/)
[![License](https://img.shields.io/github/license/LATstudio-WeFun/lat-cf-challenger?color=2EA043&style=for-the-badge)](https://github.com/LATstudio-WeFun/lat-cf-challenger)

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/jEaY4etBTY)
[![QQ](https://img.shields.io/badge/QQ-Group-12B7F5?style=for-the-badge&logo=tencent-qq&logoColor=white)](https://qm.qq.com/q/cqtKjQPRMA)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/LATstudio-WeFun/lat-cf-challenger)

</div>

---

<details open>
<summary>🇬🇧 English</summary>

### What It Does

latcf bypasses Cloudflare's protection layers:

- **Managed Challenge** — the "Verifying you are human" interstitial. latcf passes it automatically with a patched Edge/Chromium browser (~10s).
- **Turnstile** — the checkbox widget. latcf detects, engages, and resolves it with human-like cursor movement.
- **JS Challenge** — the "Checking your browser" page. Handled the same way as Managed Challenge.

Both headed and headless modes are supported.

### Install

```
pip install latcf
```

Edge/Chromium is installed automatically on first use. No extra steps.

### Quick Start

```python
import asyncio
from latcf import latch

async def main():
    cf = await latch(headless=False, turnstile=True)
    page = cf.pages[0] if cf.pages else await cf.new_page()
    await page.goto("https://hydrogen.lat")
    await cf.close()

asyncio.run(main())
```

`turnstile=True` enables the auto-solver. Detection, engagement, retry — all handled.

### API

| Function | Description |
|----------|-------------|
| `latch()` | Launch browser with auto-solve enabled |
| `latch_context()` | Launch persistent context with auto-solve |
| `relate(page)` | Is there a Turnstile widget on this page? |
| `elate(page)` | Has the Turnstile been resolved? |
| `translate(page)` | Is this a Managed Challenge interstitial? |
| `collate(page)` | Collect all Cloudflare data (cookies, tokens, etc.) |
| `plate()` | Generate a realistic user agent string |
| `plate_context(opts)` | Patch your options dict with a real UA |

### Browser Launch

```python
from latcf import latch, latch_context

cf = await latch(headless=False, turnstile=True)
page = cf.pages[0]

cf = await latch(headless=False, channel="msedge", turnstile=True)

ctx = await latch_context("./profile", headless=False, turnstile=True)

cf = await latch(headless=False, turnstile=False)

await cf.close()
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `headless` | `False` | Run in headless mode |
| `channel` | `"msedge"` | Browser channel: `msedge`, `chrome`, `chromium` |
| `turnstile` | `True` | Enable auto-solver (or pass `Latitude` for custom config) |
| `stealth` | `True` | Inject anti-detection scripts |
| `user_data_dir` | temp dir | Persistent browser profile path |

### Solver Configuration

Defaults cover most scenarios. Fine-tune if needed:

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
    managed_timeout_ms=45000,
    logger=print,
)

cf = await latch(headless=False, turnstile=opts)
```

The solver monitors page navigations, DOM changes, and reloads. Before engaging a Turnstile widget, it wanders nearby, pauses naturally, then approaches from a random angle. Managed Challenge pages are detected and allowed to auto-resolve; if they time out, a direct engagement is attempted.

### Human-Like Cursor

`Lateral` moves along bezier curves with hand tremor, wind drift, micro-corrections, and overshoot. Click timing follows a gaussian distribution.

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

### Cloudflare Inspection

```python
from latcf import relate, elate, translate, collate

found = await relate(page)       # Turnstile present?
solved = await elate(page)       # Already resolved?
managed = await translate(page)  # Managed Challenge page?
data = await collate(page)       # Collect everything
```

`collate()` returns a `CFData` object: `cf_clearance`, `turnstile_tokens`, `turnstile_sitekeys`, `cf_cookies`, `challenge_managed`, `challenge_cleared`, `storage_local`, `storage_session`, etc.

### Headless UA Patch

Headless Chrome leaks `HeadlessChrome` in the user agent. latcf replaces it automatically.

```python
from latcf import plate
ua = plate(channel="msedge")
```

Env: `LAT_CF_HEADLESS_UA=0` to disable, `LAT_CF_HEADLESS_UA=<string>` for custom.

### Use as API Backend

latcf works as a backend for your own API. FastAPI example:

```python
from fastapi import FastAPI
from latcf import latch, collate

app = FastAPI()

@app.get("/solve")
async def solve(url: str):
    cf = await latch(headless=True, turnstile=True)
    page = cf.pages[0] if cf.pages else await cf.new_page()
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
- Microsoft Edge or Google Chrome installed

</details>

---

<details>
<summary>🇨🇳 中文</summary>

### 功能

latcf 绕过 Cloudflare 的多层防护：

- **Managed Challenge** — "正在验证你是否为真人" 页面。latcf 使用修补过的 Edge/Chromium 浏览器自动通过（约 10 秒）。
- **Turnstile** — 复选框验证组件。latcf 检测、触发并以仿人类光标轨迹完成验证。
- **JS Challenge** — "正在检查你的浏览器" 页面，处理方式同 Managed Challenge。

有头模式和无头模式均支持。

### 安装

```
pip install latcf
```

Edge/Chromium 会在首次使用时自动安装，无需额外操作。

### 快速上手

```python
import asyncio
from latcf import latch

async def main():
    cf = await latch(headless=False, turnstile=True)
    page = cf.pages[0] if cf.pages else await cf.new_page()
    await page.goto("https://hydrogen.lat")
    await cf.close()

asyncio.run(main())
```

`turnstile=True` 启用自动解决器。检测、触发、重试，全部自动完成。

### API

| 函数 | 作用 |
|------|------|
| `latch()` | 启动浏览器，自动解决 Cloudflare 验证 |
| `latch_context()` | 启动持久化上下文，自动解决验证 |
| `relate(page)` | 页面上有没有 Turnstile？ |
| `elate(page)` | Turnstile 解决了没？ |
| `translate(page)` | 是不是 Managed Challenge 页面？ |
| `collate(page)` | 获取所有 Cloudflare 数据（cookie、token 等） |
| `plate()` | 生成真实的 UA 字符串 |
| `plate_context(opts)` | 给配置加上真实 UA |

### 启动浏览器

```python
from latcf import latch, latch_context

cf = await latch(headless=False, turnstile=True)
page = cf.pages[0]

cf = await latch(headless=False, channel="msedge", turnstile=True)

ctx = await latch_context("./profile", headless=False, turnstile=True)

cf = await latch(headless=False, turnstile=False)

await cf.close()
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `headless` | `False` | 无头模式 |
| `channel` | `"msedge"` | 浏览器通道：`msedge`、`chrome`、`chromium` |
| `turnstile` | `True` | 启用自动解决器（也可传入 `Latitude` 自定义配置） |
| `stealth` | `True` | 注入反检测脚本 |
| `user_data_dir` | 临时目录 | 持久化浏览器配置文件路径 |

### 解决器配置

默认配置覆盖大多数场景，需要微调时：

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
    managed_timeout_ms=45000,
    logger=print,
)

cf = await latch(headless=False, turnstile=opts)
```

解决器监听页面导航、DOM 变化、页面重载。触发 Turnstile 前，光标会在附近随机游荡、自然停顿，然后从随机角度接近。Managed Challenge 页面自动识别并等待自动通过；超时后尝试直接触发。

### 仿人类光标

`Lateral` 沿贝塞尔曲线移动，带手抖、风漂移、到达微修正、长距离过冲。触发时间遵循高斯分布。

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
| 触发 | `button` ("left")、`click_count` (1)、`hesitate` (0)、`hold_ms` (~85) |
| 滚动 | `delta_x` (0)、`delta_y` (300)、`steps` (6)、`step_delay` (60) |
| 悬停 | `duration` (500)、`jitter` (1.5) |

### Cloudflare 检查

```python
from latcf import relate, elate, translate, collate

found = await relate(page)       # 有没有 Turnstile？
solved = await elate(page)       # 解决了没？
managed = await translate(page)  # 是 Managed Challenge 页面吗？
data = await collate(page)       # 获取全部数据
```

`collate()` 返回 `CFData` 对象：`cf_clearance`、`turnstile_tokens`、`turnstile_sitekeys`、`cf_cookies`、`challenge_managed`、`challenge_cleared`、`storage_local`、`storage_session` 等。

### Headless UA 修补

Headless 模式的 UA 带 `HeadlessChrome`，会被立刻识别。latcf 自动替换成真实浏览器 UA。

```python
from latcf import plate
ua = plate(channel="msedge")
```

环境变量：`LAT_CF_HEADLESS_UA=0` 禁用，`LAT_CF_HEADLESS_UA=<字符串>` 使用自定义值。

### 作为 API 后端

latcf 可直接作为后端 API 使用。FastAPI 示例：

```python
from fastapi import FastAPI
from latcf import latch, collate

app = FastAPI()

@app.get("/solve")
async def solve(url: str):
    cf = await latch(headless=True, turnstile=True)
    page = cf.pages[0] if cf.pages else await cf.new_page()
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
- 已安装 Microsoft Edge 或 Google Chrome

</details>

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,11,6&height=100&section=footer" alt="footer" />

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/jEaY4etBTY)
[![QQ](https://img.shields.io/badge/QQ-Group-12B7F5?style=for-the-badge&logo=tencent-qq&logoColor=white)](https://qm.qq.com/q/cqtKjQPRMA)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/LATstudio-WeFun/lat-cf-challenger)

MIT License · Made by ilat

</div>
