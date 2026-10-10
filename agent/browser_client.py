
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    profile_dir = str(Path(".fomo_browser_profile").resolve())

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
        )

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(
                "https://www.fomo.family",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            print("FOMO Family page opened:", page.url)
            print("Browser session running. No trades will be placed.")

            while True:
                await asyncio.sleep(10)

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
