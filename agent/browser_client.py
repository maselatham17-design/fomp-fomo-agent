"""Inspect FOMO's sign-in page safely."""

import asyncio
from playwright.async_api import async_playwright

async def main():
async with async_playwright() as p:
browser = await p.chromium.launch(headless=True)
page = await browser.new_page()

```
    try:
        await page.goto(
            "https://www.fomo.family",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await page.wait_for_timeout(3000)

        print("PAGE URL:", page.url)
        print("PAGE TITLE:", await page.title())

        print("\nBUTTONS:")
        for item in await page.locator("button").all_text_contents():
            print("-", item.strip())

        print("\nLINKS:")
        for item in await page.locator("a").all_text_contents():
            if item.strip():
                print("-", item.strip())

        print("\nInspection complete. No trades placed.")

    finally:
        await browser.close()
```

if **name** == "**main**":
asyncio.run(main())
