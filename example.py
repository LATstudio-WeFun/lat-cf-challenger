import asyncio
import time
import tempfile
from latcf import latch, Latitude

async def main():
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

    with tempfile.TemporaryDirectory() as tmpdir:
        start = time.time()
        cf = await latch(
            headless=True, # or False
            channel="msedge",
            turnstile=opts,
            stealth=True,
            user_data_dir=tmpdir,
        )

        page = cf.pages[0]
        await page.context.clear_cookies()
        await page.goto("https://hydrogen.lat")

        clearance = None
        all_cookies = []
        for _ in range(60):
            all_cookies = await page.context.cookies()
            for c in all_cookies:
                if c["name"] == "cf_clearance" and len(c["value"]) > 20:
                    clearance = c["value"]
                    break
            if clearance:
                print(f"cf_clearance: {clearance}")
                print(f"time: {time.time() - start:.2f}s")
                break
            await asyncio.sleep(0.5)
        else:
            print("cf_clearance: ")
            print(f"time: {time.time() - start:.2f}s")
            await cf.close()
            return

        user_agent = await page.evaluate("navigator.userAgent")
        await cf.close()

if __name__ == "__main__":
    asyncio.run(main())
