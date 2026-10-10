
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    profile = Path(".fomo_browser_profile").resolve()

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=True,
        )

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(
                "https://www.fomo.family",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.wait_for_timeout(5000)

            print("URL:", page.url)
            print("TITLE:", await page.title())
            print("\nBUTTONS:")
            for item in await page.locator("button").all_text_contents():
                if item.strip():
                    print("-", item.strip())

            print("\nLINKS:")
            for item in await page.locator("a").all_text_contents():
                if item.strip():
                    print("-", item.strip())

            print("\nINSPECTION COMPLETE — NO TRADES PLACED")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
