"""fomp-fomo-agent configuration.

Secrets (bearer + refresh tokens) live in .env, never here.

IMPORTANT: fomo's developer API paths are shown inside your Developer tab.
Align BASE_URL, ENDPOINTS and RESPONSE_KEYS below with what you see there —
the core code never hardcodes a path or field name.
"""

# ---------------------------------------------------------------------------
# fomo API — align these with your Developer tab docs
# ---------------------------------------------------------------------------
BASE_URL = "https://api.fomo.family"

ENDPOINTS = {
    # Refresh the bearer token using the refresh token.
    # The client POSTs {"refresh_token": "..."} and expects at least
    # an access/bearer token back (see RESPONSE_KEYS["auth"]).
    "refresh": "/v1/auth/refresh",

    # Trending / discovery feed. Should return a list of tokens.
    "trending": "/v1/tokens/trending",

    # Token detail / price. "{address}" is substituted automatically.
    "token": "/v1/tokens/{address}",

    # Place a trade. The client POSTs the body defined in TRADE_BODY below.
    "trade": "/v1/trade",

    # Account balances (used for the pre-flight check at startup).
    "balances": "/v1/account/balances",
}

# Field-name mapping so the client can adapt to fomo's exact response shape.
RESPONSE_KEYS = {
    "auth": {
        "access_token": ["access_token", "bearer", "token"],
        "refresh_token": ["refresh_token", "refreshToken"],
        "expires_in": ["expires_in", "expiresIn"],
    },
    "token": {
        "address": ["address", "mint", "tokenAddress", "id"],
        "symbol": ["symbol", "ticker"],
        "name": ["name"],
        "price_usd": ["priceUsd", "price_usd", "price"],
        "change_short": ["priceChange5m", "change5m", "priceChange1h", "change1h"],
        "volume_usd": ["volume24hUsd", "volumeUsd", "volume"],
        "liquidity_usd": ["liquidityUsd", "liquidity"],
        "market_cap_usd": ["marketCapUsd", "marketCap", "mcap"],
    },
    # Where the token list lives inside the trending response
    # (tried in order; a bare list response also works).
    "trending_list": ["tokens", "data", "results", "items"],
    # Order/tx id in the trade response.
    "trade_id": ["txId", "orderId", "signature", "id"],
}

# Template for the trade request body. {address}, {side}, {amount_usd}
# are substituted. Adjust keys to match your Developer tab docs.
TRADE_BODY = {
    "tokenAddress": "{address}",
    "side": "{side}",            # "buy" or "sell"
    "amountUsd": "{amount_usd}", # for sells the agent sends the full position
    "chain": "solana",
    "slippageBps": 300,
}

# ---------------------------------------------------------------------------
# Discovery / entry strategy
# ---------------------------------------------------------------------------
POLL_INTERVAL_SECONDS = 20       # how often to poll trending + refresh positions

MIN_LIQUIDITY_USD = 20_000       # skip thin tokens
MAX_MARKET_CAP_USD = 5_000_000   # skip already-huge tokens
MIN_MOMENTUM_SCORE = 8.0         # minimum score to enter (see strategy.py)
NAME_BLOCKLIST = ["test", "rug", "presale"]

REENTRY_COOLDOWN_SECONDS = 1800  # don't rebuy a token within 30 min of exiting

# ---------------------------------------------------------------------------
# Position sizing & limits
# ---------------------------------------------------------------------------
BUY_AMOUNT_USD = 10.0
MAX_OPEN_POSITIONS = 3
BUY_COOLDOWN_SECONDS = 120
MAX_TRADES_PER_DAY = 30

# ---------------------------------------------------------------------------
# Exit strategy
# ---------------------------------------------------------------------------
TAKE_PROFIT_PCT = 25.0           # sell at +25% vs entry price
STOP_LOSS_PCT = -12.0            # sell at -12% vs entry price
MAX_HOLD_SECONDS = 3600          # sell after 1 hour regardless

# ---------------------------------------------------------------------------
# Data output (consumed by the fomp tracking website)
# ---------------------------------------------------------------------------
DATA_DIR = "data"
TRADES_FILE = "data/trades.json"
POSITIONS_FILE = "data/positions.json"
AUTH_CACHE_FILE = "data/auth.json"
STATS_SERVER_PORT = 8802
