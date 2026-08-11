"""Momentum ("fomo") scoring and exit rules."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import config


@dataclass
class Position:
    address: str
    symbol: str
    entry_price_usd: float
    amount_usd: float
    opened_at: float = field(default_factory=time.time)
    last_price_usd: float = 0.0

    def pnl_pct(self) -> float:
        if self.entry_price_usd <= 0 or self.last_price_usd <= 0:
            return 0.0
        return (self.last_price_usd / self.entry_price_usd - 1) * 100

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "symbol": self.symbol,
            "entry_price_usd": self.entry_price_usd,
            "last_price_usd": self.last_price_usd,
            "pnl_pct": round(self.pnl_pct(), 2),
            "amount_usd": self.amount_usd,
            "opened_at": self.opened_at,
        }


def momentum_score(token: dict) -> float:
    """Score a trending token.

    change_short (short-window % price change) is the main driver,
    dampened by log-scaled volume so a +40% move on $500 volume doesn't
    outrank a +15% move on $2M volume.
    """
    change = token["change_short"]
    if change <= 0:
        return 0.0
    volume_factor = math.log10(max(token["volume_usd"], 1) + 10) / 6  # ~0..>1
    return change * min(volume_factor, 1.5)


class Strategy:
    def __init__(self):
        self.positions: dict[str, Position] = {}
        self.recent_exits: dict[str, float] = {}   # address -> exit time
        self.last_buy_at: float = 0.0
        self.trades_today: int = 0
        self.day_start: float = time.time()

    # ------------------------------------------------------------------ entry
    def pick_entry(self, tokens: list[dict]) -> dict | None:
        """Return the best candidate to buy, or None."""
        self._roll_day()
        if self.trades_today >= config.MAX_TRADES_PER_DAY:
            return None
        if len(self.positions) >= config.MAX_OPEN_POSITIONS:
            return None
        if time.time() - self.last_buy_at < config.BUY_COOLDOWN_SECONDS:
            return None

        best, best_score = None, 0.0
        now = time.time()
        for token in tokens:
            if token["address"] in self.positions:
                continue
            exited_at = self.recent_exits.get(token["address"], 0)
            if now - exited_at < config.REENTRY_COOLDOWN_SECONDS:
                continue
            if token["liquidity_usd"] and token["liquidity_usd"] < config.MIN_LIQUIDITY_USD:
                continue
            if token["market_cap_usd"] and token["market_cap_usd"] > config.MAX_MARKET_CAP_USD:
                continue
            haystack = f"{token['name']} {token['symbol']}".lower()
            if any(word.lower() in haystack for word in config.NAME_BLOCKLIST):
                continue

            score = momentum_score(token)
            if score > best_score:
                best, best_score = token, score

        if best and best_score >= config.MIN_MOMENTUM_SCORE:
            best = dict(best)
            best["score"] = round(best_score, 2)
            return best
        return None

    def register_entry(self, token: dict) -> Position:
        pos = Position(
            address=token["address"],
            symbol=token["symbol"],
            entry_price_usd=token["price_usd"],
            amount_usd=config.BUY_AMOUNT_USD,
        )
        pos.last_price_usd = pos.entry_price_usd
        self.positions[pos.address] = pos
        self.last_buy_at = time.time()
        self.trades_today += 1
        return pos

    # ------------------------------------------------------------------- exit
    def exit_reason(self, pos: Position) -> str | None:
        pnl = pos.pnl_pct()
        if pnl >= config.TAKE_PROFIT_PCT:
            return "take_profit"
        if pnl <= config.STOP_LOSS_PCT:
            return "stop_loss"
        if time.time() - pos.opened_at >= config.MAX_HOLD_SECONDS:
            return "timeout"
        return None

    def close(self, address: str) -> Position | None:
        pos = self.positions.pop(address, None)
        if pos:
            self.recent_exits[address] = time.time()
        return pos

    # ---------------------------------------------------------------- helpers
    def _roll_day(self):
        if time.time() - self.day_start >= 86400:
            self.day_start = time.time()
            self.trades_today = 0
