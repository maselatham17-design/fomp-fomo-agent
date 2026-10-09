
"""FOMO browser automation starter.

Uses Codespaces environment secrets. Never hardcode credentials.
Does not place trades.
"""

import asyncio
import os
from playwright.async_api import async_playwright

FOMO_URL = "https://www.fomo.family"


async def main():
    username = os.getenv("FOMO_USERNAME")
    password = os.getenv("FOMO_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "Missing FOMO_USERNAME or FOMO_PASSWORD Codespaces secret."
        )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(
                FOMO_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print("FOMO page opened:", page.url)
            print("Page title:", await page.title())

            username_fields = page.locator(
                'input[autocomplete="username"], '
                'input[type="email"], '
                'input[name="username"], '
                'input[name="email"]'
            )
            password_fields = page.locator(
                'input[autocomplete="current-password"], '
                'input[type="password"]'
            )

            if (
                await username_fields.count() == 0
                or await password_fields.count() == 0
            ):
                print(
                    "Login fields were not found. "
                    "No credentials entered and no trades placed."
                )
                return

            await username_fields.first.fill(username)
            await password_fields.first.fill(password)

            print(
                "Login fields filled. Sign-in was NOT submitted; "
                "the actual login flow must be confirmed first."
            )
            print("No trades placed.")

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
