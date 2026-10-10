
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
            await page.wait_for_timeout(3000)

            print("WEBSITE:", page.url)
            print("TITLE:", await page.title())
            print(
                "LOGIN TEXT MATCHES:",
                await page.get_by_text("Login", exact=True).count(),
            )

            print("\nBUTTONS:")
            for button in await page.locator("button").all_text_contents():
                if button.strip():
                    print("-", button.strip())

            login = page.get_by_text("Login", exact=True).first

            if await login.count() > 0:
                try:
                    await login.click(timeout=10000)
                    await page.wait_for_timeout(3000)
                except Exception as error:
                    print(
                        "LOGIN CLICK ERROR:",
                        str(error).splitlines()[0],
                    )

            print("\nCURRENT PAGE:", page.url)
            print("INPUT FIELDS:")

            for field in await page.locator("input").all():
                print({
                    "type": await field.get_attribute("type"),
                    "placeholder": await field.get_attribute("placeholder"),
                    "name": await field.get_attribute("name"),
                })

            print("\nINSPECTION COMPLETE — NO TRADES PLACED")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
