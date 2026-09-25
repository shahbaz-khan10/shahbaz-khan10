"""HTTP client for the central AMS service.

AMS owns identity (via /auth/me), the permission model and all master data
(buyers, items, colors, sizes, currencies, exchange rates, suppliers). MMS
never stores copies of AMS masters: it keeps integer AMS ids plus small
denormalized display snapshots and validates/refreshes them through this client.

Every call uses the incoming caller's Bearer token, so AMS permission gating
still applies. Results are cached in-process with short TTLs (the methods that
cache are marked).
"""

import logging
import time
from typing import Any, Optional

import httpx

from django.conf import settings

logger = logging.getLogger("mms.ams_client")


def _params(**kw):
    return {k: v for k, v in kw.items() if v is not None}


class AmsClient:
    def __init__(self):
        self.base = settings.AMS_API_URL.rstrip("/")
        self.user_ttl = settings.AMS_USER_CACHE_SECONDS
        self.master_ttl = settings.AMS_MASTER_CACHE_SECONDS
        self._user_cache: dict[str, tuple[float, Optional[dict]]] = {}
        self._master_cache: dict[tuple, tuple[float, Any]] = {}
        self._timout = 10.0

    # ------------------------------------------------------------------ low level
    def request(self, method: str, path: str, token: str = "", json=None):
        url = f"{self.base}{path}"
        headers = {"Accept": "application/json"}
        if json is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = httpx.request(method, url, headers=headers, json=json, timeout=self._timout)
        except httpx.HTTPError as exc:
            logger.warning("AMS %s %s failed: %s", method, path, exc)
            return None
        if resp.status_code >= 400:
            return None
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    # ------------------------------------------------------------------ identity
    def whoami(self, token: str) -> Optional[dict]:
        """Resolves a Bearer token to the AMS user payload (/auth/me)."""
        key = token
        cached = self._user_cache.get(key)
        if cached and cached[0] > time.time():
            return cached[1]
        data = self.request("GET", "/auth/me", token=token)
        self._user_cache[key] = (time.time() + self.user_ttl, data)
        return data

    def login(self, username: str, password: str):
        data = self.request("POST", "/auth/login", json={"identifier": username, "password": password})
        if data and data.get("access_token"):
            return {"token": data["access_token"], **data}
        return data

    # ------------------------------------------------------------------ masters
    def _fetch(self, path: str, token: str, ttl: Optional[int], **params):
        key = (path, tuple(sorted(params.items())))
        cached = self._master_cache.get(key)
        if ttl and cached and cached[0] > time.time():
            return cached[1]
        data = self.request("GET", path + self._querystring(params), token=token)
        if ttl and data is not None:
            self._master_cache[key] = (time.time() + ttl, data)
        return data

    def _querystring(self, params: dict) -> str:
        from urllib.parse import urlencode

        return ("?" + urlencode(params)) if params else ""

    # per-entity by id (validates + denormalizes)
    def buyer(self, pk, token):
        return self._fetch(f"/buyers/{pk}", token, self.master_ttl)

    def item(self, pk, token):
        return self._fetch(f"/items/{pk}", token, self.master_ttl)

    def color(self, pk, token):
        return self._fetch(f"/colors/{pk}", token, self.master_ttl)

    def size(self, pk, token):
        return self._fetch(f"/sizes/{pk}", token, self.master_ttl)

    def currency(self, pk, token):
        return self._fetch(f"/currencies/{pk}", token, self.master_ttl)

    def supplier(self, pk, token):
        return self._fetch(f"/suppliers/{pk}", token, self.master_ttl)

    def fetch_user(self, pk, token):
        return self._fetch(f"/users/{pk}", token, self.master_ttl)

    # lists (used for dropdowns by the UI as well as validation)
    def list_buyers(self, token, search="", page_size=200):
        return self._fetch("/buyers", token, None, search=search, page_size=page_size)

    def list_items(self, token, search="", page_size=200):
        return self._fetch("/items", token, self.master_ttl, search=search, page_size=page_size)

    def list_colors(self, token, page_size=200):
        return self._fetch("/colors", token, self.master_ttl, page_size=page_size)

    def list_sizes(self, token, page_size=200):
        return self._fetch("/sizes", token, self.master_ttl, page_size=page_size)

    def list_currencies(self, token, page_size=200):
        return self._fetch("/currencies", token, self.master_ttl, page_size=page_size)

    def list_exchange_rates(self, token, from_currency_id=None, to_currency_id=None, page_size=1):
        return self._fetch(
            "/exchange-rates", token, self.master_ttl,
            from_currency_id=from_currency_id, to_currency_id=to_currency_id, page_size=page_size,
        )

    def exchange_rate(self, from_id, to_id, token) -> Optional[float]:
        """Latest AMS rate for `from`->`to` (falls back to inverse, then 1.0)."""
        if from_id == to_id:
            return 1.0
        data = self.list_exchange_rates(token, from_currency_id=from_id, to_currency_id=to_id)
        if data and data.get("items"):
            return float(data["items"][0]["rate"])
        inverse = self.list_exchange_rates(token, from_currency_id=to_id, to_currency_id=from_id)
        if inverse and inverse.get("items"):
            rate = float(inverse["items"][0]["rate"])
            return 1.0 / rate if rate else None
        return None

    # ------------------------------------------------------------------ audit
    def audit(self, action: str, entity_type: str, entity_id, label: str, token: str, notes: str = "") -> bool:
        """Writes an audit entry into the central AMS log. Returns success."""
        try:
            result = self.request(
                "POST",
                "/audit/logs",
                token=token,
                json={
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "entity_label": label,
                    "notes": notes,
                },
            )
            return result is not None
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit write failed: %s", exc)
            return False


ams = AmsClient()