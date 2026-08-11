"""Bearer + refresh token lifecycle for the fomo API.

- Loads FOMO_BEARER_TOKEN and FOMO_REFRESH_TOKEN from the environment (.env),
  copied from the Developer tab in the fomo app.
- Sends `Authorization: Bearer <token>` on every request.
- On 401 (or near known expiry) it calls the refresh endpoint, swaps in the
  new bearer token — and the new refresh token if rotation is used — then
  retries the original request once.
- Persists the freshest tokens to data/auth.json (gitignored) so a restart
  never reuses a stale bearer token.
"""

from __future__ import annotations

import json
import logging
import os
import time

import aiohttp

import config

log = logging.getLogger("fomp.fomo.auth")


def _pick(d: dict, candidates: list[str]):
    for key in candidates:
        if key in d and d[key] is not None:
            return d[key]
    return None


class AuthManager:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.bearer: str = ""
        self.refresh_token: str = ""
        self.expires_at: float | None = None  # epoch seconds, if known
        self._refresh_lock = None  # created lazily inside the event loop
        self._load()

    # ----------------------------------------------------------------- setup
    def _load(self):
        # Prefer cached (freshest) tokens over the ones in .env
        cached = {}
        try:
            with open(config.AUTH_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        self.bearer = cached.get("bearer") or os.environ.get("FOMO_BEARER_TOKEN", "")
        self.refresh_token = cached.get("refresh_token") or os.environ.get("FOMO_REFRESH_TOKEN", "")
        self.expires_at = cached.get("expires_at")

        if not self.bearer or not self.refresh_token:
            raise RuntimeError(
                "FOMO_BEARER_TOKEN and FOMO_REFRESH_TOKEN must be set in .env "
                "(copy them from the Developer tab in the fomo app)."
            )

    def _save(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(config.AUTH_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"bearer": self.bearer,
                 "refresh_token": self.refresh_token,
                 "expires_at": self.expires_at},
                f, indent=2,
            )

    # --------------------------------------------------------------- refresh
    async def refresh(self) -> bool:
        """Exchange the refresh token for a new bearer token."""
        import asyncio
        if self._refresh_lock is None:
            self._refresh_lock = asyncio.Lock()
        async with self._refresh_lock:
            url = config.BASE_URL + config.ENDPOINTS["refresh"]
            try:
                async with self.session.post(
                    url,
                    json={"refresh_token": self.refresh_token},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.json(content_type=None)
                    if resp.status != 200:
                        log.error("token refresh failed status=%s body=%s", resp.status, body)
                        return False
            except Exception:
                log.exception("token refresh request error")
                return False

            keys = config.RESPONSE_KEYS["auth"]
            new_bearer = _pick(body, keys["access_token"])
            if not new_bearer:
                log.error("refresh response missing access token: %s", body)
                return False
            self.bearer = new_bearer

            new_refresh = _pick(body, keys["refresh_token"])
            if new_refresh:  # refresh-token rotation
                self.refresh_token = new_refresh

            expires_in = _pick(body, keys["expires_in"])
            if expires_in:
                self.expires_at = time.time() + float(expires_in)

            self._save()
            log.info("bearer token refreshed")
            return True

    def _near_expiry(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at - 60

    # --------------------------------------------------------------- request
    async def request(self, method: str, path_or_url: str, **kwargs) -> tuple[int, dict | list | None]:
        """Authenticated request with one automatic refresh+retry on 401."""
        url = path_or_url if path_or_url.startswith("http") else config.BASE_URL + path_or_url

        if self._near_expiry():
            await self.refresh()

        for attempt in (1, 2):
            headers = dict(kwargs.pop("headers", {}) or {})
            headers["Authorization"] = f"Bearer {self.bearer}"
            try:
                async with self.session.request(
                    method, url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20), **kwargs,
                ) as resp:
                    try:
                        body = await resp.json(content_type=None)
                    except Exception:
                        body = None
                    if resp.status == 401 and attempt == 1:
                        log.info("401 received, refreshing bearer token")
                        if await self.refresh():
                            continue
                    return resp.status, body
            except Exception:
                log.exception("%s %s request error", method, url)
                return 0, None
        return 401, None
