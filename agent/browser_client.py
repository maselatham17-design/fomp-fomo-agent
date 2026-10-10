
"""Persistent FOMO Family browser session.

Opens FOMO Family and keeps the browser session alive.
Log in manually if prompted. This version does not place trades.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    profile_dir = Path(".fomo_browser_profile").resolve()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 900},
        )

        try:
            page = (
                context.pages[0]
                if context.pages
                else await context.new_page()
            )

            await page.goto(
                "https://www.fomo.family",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print("FOMO Family browser session started.")
            print("Page:", page.url)
            print("This script does not buy or sell.")
            print("Press Ctrl+C in the terminal to stop.")

            while True:
                await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("Stopping browser session.")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
