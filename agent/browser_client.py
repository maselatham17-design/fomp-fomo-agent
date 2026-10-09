
"""Browser-based FOMO Family login using Playwright."""

import asyncio
import os

from playwright.async_api import async_playwright

FOMO_URL = "https://www.fomo.family"


async def main():
    username = os.getenv("FOMO_USERNAME")
    password = os.getenv("FOMO_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "Set FOMO_USERNAME and FOMO_PASSWORD as environment secrets."
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

            # Find common login controls without assuming exact selectors.
            user_field = page.locator(
                'input[autocomplete="username"], '
                'input[type="email"], input[name="username"], '
                'input[name="email"]'
            ).first

            password_field = page.locator(
                'input[autocomplete="current-password"], '
                'input[type="password"]'
            ).first

            if await user_field.count() == 0 or await password_field.count() == 0:
                print(
                    "Login fields were not found on the initial page. "
                    "The site's login flow may require clicking a login button "
                    "or navigating to a sign-in page."
                )
                return

            await user_field.fill(username)
            await password_field.fill(password)

            print("Login fields filled. Review the site's sign-in flow.")
            print("No trade has been submitted.")

            # Deliberately do not guess which button submits login.
            # Confirm the actual login page before adding that action.

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
