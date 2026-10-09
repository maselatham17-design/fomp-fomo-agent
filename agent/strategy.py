
"""Momentum scoring, entry filters, and position exit rules."""

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


def _number(token: dict, key: str) -> float | None:
    """Return a finite numeric field, or None if missing/invalid."""
    try:
        value = float(token[key])
        return value if math.isfinite(value) else None
    except (KeyError, TypeError, ValueError):
        return None


def momentum_score(token: dict) -> float:
    """Reward positive momentum supported by meaningful trading volume."""
    change = _number(token, "change_short")
    volume = _number(token, "volume_usd")

    if change is None or volume is None or change <= 0 or volume <= 0:
        return 0.0

    # Volume contributes to confidence but cannot overwhelm price momentum.
    volume_factor = min(math.log10(volume + 10) / 6, 1.5)
    score = change * volume_factor

    # Penalize extreme short-window spikes instead of chasing them blindly.
    if change >= 50:
        score *= 0.5
    elif change >= 30:
        score *= 0.75

    # Prefer tokens whose recent momentum is not sharply deteriorating,
    # when the data provider supplies a longer-window change.
    longer_change = _number(token, "change_long")
    if longer_change is not None and longer_change < 0:
        score *= 0.7

    return max(score, 0.0)


class Strategy:
    def __init__(self):
        self.positions: dict[str, Position] = {}
        self.recent_exits: dict[str, float] = {}
        self.last_buy_at = 0.0
        self.trades_today = 0
        self.day_start = time.time()

    def pick_entry(self, tokens: list[dict]) -> dict | None:
        """Choose the highest-scoring candidate that passes safety filters."""
        self._roll_day()

        if self.trades_today >= config.MAX_TRADES_PER_DAY:
            return None
        if len(self.positions) >= config.MAX_OPEN_POSITIONS:
            return None
        if time.time() - self.last_buy_at < config.BUY_COOLDOWN_SECONDS:
            return None

        best = None
        best_score = 0.0
        now = time.time()

        for token in tokens:
            address = token.get("address")
            if not isinstance(address, str) or not address.strip():
                continue
            if address in self.positions:
                continue

            exited_at = self.recent_exits.get(address, 0)
            if now - exited_at < config.REENTRY_COOLDOWN_SECONDS:
                continue

            liquidity = _number(token, "liquidity_usd")
            market_cap = _number(token, "market_cap_usd")
            price = _number(token, "price_usd")
            volume = _number(token, "volume_usd")
            change = _number(token, "change_short")

            # Fail closed if required safety/market data is missing.
            if any(v is None for v in (
                liquidity, market_cap, price, volume, change
            )):
                continue
            if liquidity < config.MIN_LIQUIDITY_USD:
                continue
            if market_cap <= 0 or market_cap > config.MAX_MARKET_CAP_USD:
                continue
            if price <= 0 or volume <= 0 or change <= 0:
                continue

            name = str(token.get("name", ""))
            symbol = str(token.get("symbol", ""))
            haystack = f"{name} {symbol}".lower()
            if any(
                str(word).lower() in haystack
                for word in config.NAME_BLOCKLIST
            ):
                continue

            score = momentum_score(token)
            if score > best_score:
                best = token
                best_score = score

        if best is not None and best_score >= config.MIN_MOMENTUM_SCORE:
            result = dict(best)
            result["score"] = round(best_score, 2)
            return result
        return None

    def register_entry(self, token: dict) -> Position:
        """Record a position after the caller confirms a successful buy."""
        address = token["address"]
        price = float(token["price_usd"])

        if not math.isfinite(price) or price <= 0:
            raise ValueError("Cannot register a position with an invalid price.")
        if address in self.positions:
            raise ValueError("Position already exists for this token.")

        pos = Position(
            address=address,
            symbol=str(token.get("symbol", "UNKNOWN")),
            entry_price_usd=price,
            amount_usd=config.BUY_AMOUNT_USD,
        )
        pos.last_price_usd = price
        self.positions[address] = pos
        self.last_buy_at = time.time()
        self.trades_today += 1
        return pos

    def exit_reason(self, pos: Position) -> str | None:
        """Return an exit signal; the execution layer must submit the sell."""
        pnl = pos.pnl_pct()

        if pnl >= config.TAKE_PROFIT_PCT:
            return "take_profit"
        if pnl <= config.STOP_LOSS_PCT:
            return "stop_loss"
        if time.time() - pos.opened_at >= config.MAX_HOLD_SECONDS:
            return "timeout"
        return None

    def close(self, address: str) -> Position | None:
        """Remove a position only after the caller confirms a successful sell."""
        pos = self.positions.pop(address, None)
        if pos:
            self.recent_exits[address] = time.time()
        return pos

    def _roll_day(self):
        if time.time() - self.day_start >= 86400:
            self.day_start = time.time()
            self.trades_today = 0
