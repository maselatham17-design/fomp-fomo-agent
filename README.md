# fomp-fomo-agent

Part of the **fomp** project. An automated momentum ("fomo") trading agent for the [fomo](https://fomo.family) social trading platform, authenticated with the **Bearer token + Refresh token from the Developer tab** in your fomo account.

The agent polls fomo's trending/discovery feed, scores tokens by short-term momentum, buys the strongest candidate with a fixed USD size, and manages every position with take-profit, stop-loss, and max-hold-time exits. All fills are written to `data/trades.json` in the same schema as `fomp-pump-agent`, so the fomp tracking website can consume both agents identically.

## Authentication: Bearer + Refresh token

fomo's Developer tab gives you two values:

- **Bearer token** — short-lived access token sent as `Authorization: Bearer <token>` on every API call.
- **Refresh token** — long-lived token used to mint a new bearer token when the old one expires.

`agent/auth.py` handles the full lifecycle:

1. Loads both tokens from `.env` on first start.
2. Sends the bearer token on every request.
3. On a `401` (or proactively near expiry, if the refresh response includes `expires_in`), calls the refresh endpoint with the refresh token, swaps in the new bearer token (and new refresh token if one is returned — refresh-token rotation is supported), and retries the request once.
4. Persists the freshest tokens to `data/auth.json` (gitignored) so restarts don't reuse a stale token.

## ⚙️ Important: endpoint paths are configurable

fomo's developer API is not publicly documented — the exact endpoint paths are shown to you inside the Developer tab. This repo therefore keeps **every path in one place**: the `ENDPOINTS` dict in `config.py`, with sensible defaults. Before first run, open your Developer tab / API docs and make the paths match. You should never need to touch the core code — only `config.py`.

The client also has a `RESPONSE_KEYS` mapping so you can adapt to the exact field names fomo returns (price, symbol, address, etc.) without code changes.

## How it works

```
        every POLL_INTERVAL_SECONDS
┌────────────────┐    score by momentum     ┌──────────┐
│ GET trending    ├────────────────────────▶│ strategy │──▶ POST trade (buy)
└────────────────┘  (Δprice short window,   └────┬─────┘
                     volume, min liquidity)      │
┌────────────────┐                               │ TP / SL / timeout
│ GET token price ├──────────────────────────────┴──▶ POST trade (sell)
└────────────────┘                                   │
                                          data/trades.json + positions.json
```

1. **Discover** – poll the trending endpoint on an interval.
2. **Score** – each candidate gets a momentum score from its short-window price change and volume; tokens below `MIN_LIQUIDITY_USD` or above `MAX_MARKET_CAP_USD` are dropped, as are blocklisted names and tokens already held or recently traded (re-entry cooldown).
3. **Enter** – if the top score beats `MIN_MOMENTUM_SCORE` and limits allow, buy `BUY_AMOUNT_USD` via the trade endpoint.
4. **Manage** – every cycle, refresh the price of held tokens; sell 100% on take-profit, stop-loss, or max hold time.
5. **Record** – all fills go to `data/trades.json`; open positions to `data/positions.json`.

## Setup

Requires Python 3.10+.

```bash
git clone <your-repo-url> fomp-fomo-agent
cd fomp-fomo-agent
pip install -r requirements.txt
cp .env.example .env
```

Then:

1. In the fomo app/web, open the **Developer tab** and copy the **Bearer token** and **Refresh token** into `.env`.
2. In `config.py`, set `BASE_URL` and align the `ENDPOINTS` paths with what the Developer tab documents.
3. Tune strategy settings in `config.py`.

## Run

```bash
DRY_RUN=1 python main.py   # recommended first: full pipeline, no real orders
python main.py             # live
```

Serve data for the fomp website:

```bash
python stats_server.py     # http://localhost:8802/trades /positions /summary
```

## Trade log schema (shared with fomp-pump-agent)

```json
{
  "agent": "fomo",
  "ts": "2026-08-11T12:34:56Z",
  "side": "buy",
  "mint": "<token address>",
  "symbol": "ABC",
  "amount_usd": 10.0,
  "price_usd": 0.00042,
  "reason": "entry | take_profit | stop_loss | timeout",
  "tx": "<order/tx id or null>",
  "dry_run": false
}
```

## Files

| File | Purpose |
|---|---|
| `main.py` | Poll loop: discovery, entries, position management |
| `config.py` | Base URL, endpoint paths, response-key mapping, strategy settings |
| `agent/auth.py` | Bearer/refresh token lifecycle with auto-refresh + persistence |
| `agent/fomo_api.py` | API client (trending, price, trade, balances) |
| `agent/strategy.py` | Momentum scoring + exit rules |
| `agent/tracker.py` | JSON trade/position persistence |
| `stats_server.py` | Optional read-only HTTP server for the tracking site |
