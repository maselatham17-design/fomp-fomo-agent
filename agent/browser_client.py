
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

            await page.get_by_role("button", name="login", exact=True).click()
            await page.wait_for_timeout(3000)

            print("LOGIN PAGE URL:", page.url)
            print("PAGE TITLE:", await page.title())
            print("\nINPUT FIELDS:")
            for field in await page.locator("input").all():
                print({
                    "type": await field.get_attribute("type"),
                    "placeholder": await field.get_attribute("placeholder"),
                    "name": await field.get_attribute("name"),
                })

            print("\nBUTTONS:")
            for text in await page.locator("button").all_text_contents():
                if text.strip():
                    print("-", text.strip())

            print("\nLOGIN INSPECTION COMPLETE — NO TRADES PLACED")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
