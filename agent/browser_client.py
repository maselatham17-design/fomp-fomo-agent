
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
            await page.wait_for_timeout(3000)

            login = page.get_by_text("Login", exact=True).first

            print("START URL:", page.url)
            print("LOGIN MATCHES:", await login.count())

            if await login.count():
                print(
                    "LOGIN ELEMENT:",
                    await login.evaluate(
                        """el => ({
                            tag: el.tagName,
                            text: el.innerText,
                            href: el.getAttribute('href'),
                            role: el.getAttribute('role'),
                            html: el.outerHTML.slice(0, 1000)
                        })"""
                    ),
                )

                try:
                    await login.click(timeout=10000)
                    await page.wait_for_timeout(5000)
                except Exception as error:
                    print("CLICK ERROR:", str(error).splitlines()[0])

            print("END URL:", page.url)
            print("TITLE:", await page.title())
            print("INPUT COUNT:", await page.locator("input").count())
            print("PAGE TEXT:", (await page.locator("body").inner_text())[:1500])
            print("INSPECTION COMPLETE — NO TRADES PLACED")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
