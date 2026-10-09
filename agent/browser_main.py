
"""Entry point for the FOMO browser automation."""

import asyncio
from agent.browser_client import main as browser_main


if __name__ == "__main__":
    asyncio.run(browser_main())
