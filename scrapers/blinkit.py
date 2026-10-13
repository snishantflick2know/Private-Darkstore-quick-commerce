"""Blinkit (unofficial) search scraper.

Reverse-engineered from blinkit.com's consumer-web client. No login required for
browsing/search. Cloudflare blocks plain HTTP clients on TLS fingerprint, so we use
`curl_cffi` with `impersonate="chrome"` to pass as a real Chrome TLS handshake.

NOTE: this talks to a private/internal API, not a published partner API. It is a
reasonable approach for a pitch demo / internal prototype, but is against Blinkit's
Terms of Service and could break or get rate-limited/blocked at any time. For a
production deployment, use a licensed data partner or negotiate direct data access
instead of relying on this.
"""
from __future__ import annotations

import logging
import uuid
from typing import List

from curl_cffi import requests as cfr

from .base import ProductSnapshot

logger = logging.getLogger(__name__)

BASE_URL = "https://blinkit.com"
# Fixed constant used by the web client when bootstrapping an auth_key. Not a secret;
# it's shipped inside blinkit.com's public JS bundle.
REQ_KEY = "c0e6868e-1180-400c-be51-f473479f1f0a"


class BlinkitScraper:
    platform = "blinkit"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._auth_key: str | None = None
        self.device_id = uuid.uuid4().hex[:16]
        self.session_uuid = str(uuid.uuid4())

    def _get_auth_key(self) -> str:
        if self._auth_key:
            return self._auth_key
        r = cfr.get(
            f"{BASE_URL}/v2/accounts/auth_key/",
            headers={"req_key": REQ_KEY},
            impersonate="chrome",
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"Blinkit auth_key bootstrap failed: {data}")
        self._auth_key = data["auth_key"]
        return self._auth_key

    def _headers(self, lat: float, lon: float) -> dict:
        return {
            "auth_key": self._get_auth_key(),
            "app_client": "consumer_web",
            "platform": "desktop_web",
            "device_id": self.device_id,
            "session_uuid": self.session_uuid,
            "lat": str(lat),
            "lon": str(lon),
            "app_version": "52434332",
            "web_app_version": "1008010016",
            "content-type": "application/json",
        }

    def search(self, query: str, lat: float, lon: float, location_name: str, pincode: str) -> List[ProductSnapshot]:
        """Run a search query at a given lat/lon and return normalized product snapshots."""
        headers = self._headers(lat, lon)
        body = {
            "applied_filters": None,
            "sort": None,
            "postback_meta": {},
            "previous_search_query": "",
            "vertical_cards_processed": [],
        }
        r = cfr.post(
            f"{BASE_URL}/v1/layout/search",
            params={"q": query, "search_type": "type_to_search"},
            headers=headers,
            json=body,
            impersonate="chrome",
            timeout=self.timeout,
        )
        r.raise_for_status()
        payload = r.json()
        if not payload.get("is_success"):
            logger.warning("Blinkit search for %r returned is_success=false", query)
            return []

        snapshots: List[ProductSnapshot] = []
        for snippet in payload.get("response", {}).get("snippets", []):
            data = snippet.get("data", {})
            cart_item = (
                data.get("atc_action", {})
                .get("add_to_cart", {})
                .get("cart_item")
            )
            if not cart_item:
                continue  # not a product card (header, banner, etc.)

            snapshots.append(
                ProductSnapshot(
                    platform=self.platform,
                    location_name=location_name,
                    pincode=pincode,
                    merchant_id=str(cart_item.get("merchant_id", "")),
                    query=query,
                    product_id=str(cart_item.get("product_id", "")),
                    brand=cart_item.get("brand") or "Unknown",
                    name=cart_item.get("display_name") or cart_item.get("product_name", ""),
                    unit=cart_item.get("unit", ""),
                    price=float(cart_item.get("price") or 0),
                    mrp=float(cart_item.get("mrp") or 0),
                    inventory=int(data.get("inventory", cart_item.get("inventory", 0)) or 0),
                    is_sold_out=bool(data.get("is_sold_out", False)),
                )
            )
        return snapshots
