
"""Browser session for FOMO Family.

Opens a visible browser and lets the user sign in manually.
Does not store a password in source code or automate an order yet.
"""

import asyncio
from playwright.async_api import async_playwright


FOMO_URL = "https://www.fomo.family"


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(FOMO_URL, wait_until="domcontentloaded")
        print("FOMO opened. Sign in manually in the browser.")
        print("Keep this browser session open while working.")

        try:
            while True:
                await asyncio.sleep(2)
                if page.is_closed():
                    break
        except KeyboardInterrupt:
            pass
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
