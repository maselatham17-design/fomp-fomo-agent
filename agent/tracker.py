"""Persists trades and open positions as JSON for the fomp tracking website.

Schema is shared with fomp-pump-agent so one frontend can consume both.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

import config

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir():
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _read(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def record_trade(
    side: str,
    address: str,
    symbol: str,
    amount_usd: float,
    price_usd: float,
    reason: str,
    tx: str | None,
    dry_run: bool,
):
    entry = {
        "agent": "fomo",
        "ts": _now(),
        "side": side,
        "mint": address,
        "symbol": symbol,
        "amount_usd": amount_usd,
        "price_usd": price_usd,
        "reason": reason,
        "tx": tx,
        "dry_run": dry_run,
    }
    with _lock:
        _ensure_dir()
        trades = _read(config.TRADES_FILE, [])
        trades.append(entry)
        _write(config.TRADES_FILE, trades)


def save_positions(positions: dict):
    with _lock:
        _ensure_dir()
        _write(
            config.POSITIONS_FILE,
            {"agent": "fomo", "updated": _now(),
             "positions": [p.to_dict() for p in positions.values()]},
        )


def summary() -> dict:
    trades = _read(config.TRADES_FILE, [])
    buys = [t for t in trades if t["side"] == "buy"]
    sells = [t for t in trades if t["side"] == "sell"]
    return {
        "agent": "fomo",
        "total_trades": len(trades),
        "buys": len(buys),
        "sells": len(sells),
        "usd_deployed": round(sum(t.get("amount_usd") or 0 for t in buys), 2),
        "last_trade": trades[-1]["ts"] if trades else None,
    }
