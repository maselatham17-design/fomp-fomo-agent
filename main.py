"""fomp-fomo-agent — momentum trading agent for the fomo platform.

Auth: Bearer token + Refresh token from the Developer tab (see .env.example).

Run:  DRY_RUN=1 python main.py   (recommended first)
      python main.py             (live)
"""

from __future__ import annotations

import asyncio
import logging
import os

import aiohttp
from dotenv import load_dotenv

import config
from agent import tracker
from agent.auth import AuthManager
from agent.fomo_api import FomoClient
from agent.strategy import Strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("fomp.fomo")


class FomoAgent:
    def __init__(self, client: FomoClient):
        self.client = client
        self.strategy = Strategy()

    async def startup_check(self):
        """Verify the tokens work before entering the trade loop."""
        balances = await self.client.balances()
        if balances is None:
            log.warning(
                "balance check failed — verify BASE_URL and ENDPOINTS in "
                "config.py match your Developer tab, and that the bearer/"
                "refresh tokens in .env are current. Continuing anyway."
            )
        else:
            log.info("auth ok, balances endpoint reachable")

    async def cycle(self):
        # 1) manage open positions first (exits before entries)
        for address in list(self.strategy.positions.keys()):
            await self.update_position(address)

        # 2) look for a new entry
        tokens = await self.client.trending()
        if not tokens:
            return
        candidate = self.strategy.pick_entry(tokens)
        if candidate:
            await self.enter(candidate)

    async def enter(self, token: dict):
        log.info(
            "ENTRY %s (%s) score=%.2f price=$%.8f vol=$%.0f",
            token["name"], token["symbol"], token.get("score", 0),
            token["price_usd"], token["volume_usd"],
        )
        tx = await self.client.trade("buy", token["address"], config.BUY_AMOUNT_USD)
        if tx is None and not self.client.dry_run:
            log.warning("buy failed for %s, not opening position", token["address"])
            return
        pos = self.strategy.register_entry(token)
        tracker.record_trade(
            "buy", pos.address, pos.symbol, pos.amount_usd,
            pos.entry_price_usd, "entry", tx, self.client.dry_run,
        )
        tracker.save_positions(self.strategy.positions)

    async def update_position(self, address: str):
        pos = self.strategy.positions.get(address)
        if not pos:
            return
        token = await self.client.token(address)
        if token:
            pos.last_price_usd = token["price_usd"]
            tracker.save_positions(self.strategy.positions)

        reason = self.strategy.exit_reason(pos)
        if not reason:
            return

        log.info("EXIT %s: %s at $%.8f (entry $%.8f, pnl %+.1f%%)",
                 pos.symbol, reason, pos.last_price_usd,
                 pos.entry_price_usd, pos.pnl_pct())
        # Sell the full position (entry size adjusted by pnl as USD estimate)
        est_value = pos.amount_usd * (1 + pos.pnl_pct() / 100)
        tx = await self.client.trade("sell", address, round(est_value, 2))
        self.strategy.close(address)
        tracker.record_trade(
            "sell", pos.address, pos.symbol, pos.amount_usd,
            pos.last_price_usd, reason, tx, self.client.dry_run,
        )
        tracker.save_positions(self.strategy.positions)

    async def run(self):
        await self.startup_check()
        log.info("polling every %ss", config.POLL_INTERVAL_SECONDS)
        while True:
            try:
                await self.cycle()
            except Exception:
                log.exception("cycle error")
            await asyncio.sleep(config.POLL_INTERVAL_SECONDS)


async def main():
    load_dotenv()
    if os.environ.get("DRY_RUN", "0") == "1":
        log.warning("DRY RUN mode: no real orders will be sent")
    async with aiohttp.ClientSession() as session:
        auth = AuthManager(session)
        agent = FomoAgent(FomoClient(auth))
        await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
