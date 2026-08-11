"""Client for the fomo trading API.

All endpoint paths and response field names come from config.py so the
agent can be aligned with the Developer tab docs without code changes.
"""

from __future__ import annotations

import logging
import os

import config
from agent.auth import AuthManager

log = logging.getLogger("fomp.fomo.api")


def _pick(d: dict, candidates: list[str]):
    for key in candidates:
        if key in d and d[key] is not None:
            return d[key]
    return None


def normalize_token(raw: dict) -> dict | None:
    """Map a raw token object from fomo into the agent's internal shape."""
    keys = config.RESPONSE_KEYS["token"]
    address = _pick(raw, keys["address"])
    price = _pick(raw, keys["price_usd"])
    if not address or price is None:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None

    def num(field, default=0.0):
        val = _pick(raw, keys[field])
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    return {
        "address": str(address),
        "symbol": str(_pick(raw, keys["symbol"]) or "?"),
        "name": str(_pick(raw, keys["name"]) or ""),
        "price_usd": price,
        "change_short": num("change_short"),
        "volume_usd": num("volume_usd"),
        "liquidity_usd": num("liquidity_usd"),
        "market_cap_usd": num("market_cap_usd"),
    }


class FomoClient:
    def __init__(self, auth: AuthManager):
        self.auth = auth
        self.dry_run = os.environ.get("DRY_RUN", "0") == "1"

    async def trending(self) -> list[dict]:
        status, body = await self.auth.request("GET", config.ENDPOINTS["trending"])
        if status != 200 or body is None:
            log.warning("trending fetch failed status=%s", status)
            return []
        raw_list = body if isinstance(body, list) else None
        if raw_list is None and isinstance(body, dict):
            for key in config.RESPONSE_KEYS["trending_list"]:
                if isinstance(body.get(key), list):
                    raw_list = body[key]
                    break
        if raw_list is None:
            log.warning("could not locate token list in trending response")
            return []
        tokens = [t for t in (normalize_token(r) for r in raw_list if isinstance(r, dict)) if t]
        return tokens

    async def token(self, address: str) -> dict | None:
        path = config.ENDPOINTS["token"].format(address=address)
        status, body = await self.auth.request("GET", path)
        if status != 200 or not isinstance(body, dict):
            log.warning("token fetch failed for %s status=%s", address, status)
            return None
        # Some APIs nest the token object; try common wrappers.
        for candidate in (body, body.get("token"), body.get("data")):
            if isinstance(candidate, dict):
                normalized = normalize_token(candidate)
                if normalized:
                    return normalized
        return None

    async def balances(self) -> dict | list | None:
        status, body = await self.auth.request("GET", config.ENDPOINTS["balances"])
        return body if status == 200 else None

    async def trade(self, side: str, address: str, amount_usd: float) -> str | None:
        """Place a trade. Returns the order/tx id, or None on failure."""
        if self.dry_run:
            log.info("[DRY RUN] %s %s $%.2f", side, address, amount_usd)
            return None

        body = {}
        for key, template in config.TRADE_BODY.items():
            if isinstance(template, str):
                value = (template
                         .replace("{address}", address)
                         .replace("{side}", side)
                         .replace("{amount_usd}", str(amount_usd)))
                # Keep pure numbers numeric
                if template == "{amount_usd}":
                    value = amount_usd
                body[key] = value
            else:
                body[key] = template

        status, resp = await self.auth.request("POST", config.ENDPOINTS["trade"], json=body)
        if status == 200 and isinstance(resp, dict):
            trade_id = _pick(resp, config.RESPONSE_KEYS["trade_id"])
            log.info("%s %s $%.2f ok id=%s", side, address, amount_usd, trade_id)
            return str(trade_id) if trade_id else "ok"
        log.error("trade failed status=%s body=%s", status, resp)
        return None
