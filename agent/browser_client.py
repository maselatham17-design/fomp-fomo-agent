
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    profile = Path(".fomo_browser_profile").resolve()

    async with async_playwright() as playwright:
        browser_context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=True,
        )

        try:
            page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
            await page.goto("https://www.fomo.family", wait_until="domcontentloaded", timeout=60000)
            print("FOMO Family opened:", page.url)
            print("Session running. This script does not place trades.")

            while True:
                await asyncio.sleep(10)

        finally:
            await browser_context.close()


if __name__ == "__main__":
    asyncio.run(main())
