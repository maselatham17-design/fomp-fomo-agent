
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    profile = Path(".fomo_browser_profile").resolve()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=True,
        )

        try:
            page = context.pages[0] if context.pages else await context.new_page()

            await page.goto(
                "https://fomo.family/",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.wait_for_timeout(3000)

            login = page.get_by_text("Login", exact=True).first
            print("LOGIN MATCHES:", await login.count())

            if await login.count():
                print(
                    "LOGIN HTML:",
                    await login.evaluate(
                        "el => el.closest('button, a')?.outerHTML || el.outerHTML"
                    ),
                )

                print(
                    "LOGIN PARENT:",
                    await login.evaluate(
                        "el => el.parentElement?.outerHTML.slice(0, 1500)"
                    ),
                )

            print("URL:", page.url)
            print("INSPECTION COMPLETE — NO TRADES PLACED")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
