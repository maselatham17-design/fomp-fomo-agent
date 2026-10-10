
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

            print("START URL:", page.url)

            login = page.get_by_text("Login", exact=True).first
            print("LOGIN MATCHES:", await login.count())

            if await login.count():
                try:
                    async with page.expect_popup(timeout=5000) as popup_info:
                        await login.click(timeout=10000)

                    popup = await popup_info.value
                    await popup.wait_for_load_state(
                        "domcontentloaded", timeout=15000
                    )
                    print("POPUP URL:", popup.url)
                    print("POPUP TITLE:", await popup.title())

                except Exception as error:
                    print("NO POPUP OR CLICK ISSUE:", str(error).splitlines()[0])

            print("FINAL URL:", page.url)
            print("PAGE COUNT:", len(context.pages))
            print("INPUT COUNT:", await page.locator("input").count())
            print("INSPECTION COMPLETE — NO TRADES PLACED")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
