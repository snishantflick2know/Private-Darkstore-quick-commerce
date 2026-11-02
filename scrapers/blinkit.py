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
import time
import uuid
from typing import List

from curl_cffi import requests as cfr

from .base import ProductSnapshot

logger = logging.getLogger(__name__)

BASE_URL = "https://blinkit.com"
# Fixed constant used by the web client when bootstrapping an auth_key. Not a secret;
# it's shipped inside blinkit.com's public JS bundle.
REQ_KEY = "c0e6868e-1180-400c-be51-f473479f1f0a"


class RateLimitedError(Exception):
    """Raised when Blinkit returns HTTP 429. Deliberately distinct from returning
    None/empty results, so callers never mistake "we got rate-limited" for "this
    store genuinely doesn't carry the product"."""


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

    PAGE_SIZE = 12

    def get_merchants(self, lat: float, lon: float) -> List[dict]:
        """Returns ALL dark stores Blinkit considers serviceable for this point, not
        just the nearest one. A single area can have multiple real stores with
        completely independent stock - the search endpoint always auto-resolves to
        the nearest one (rank 1) and ignores any merchant_id override, so this is
        how you discover the others to check individually via `get_product_at_merchant`.
        """
        headers = self._headers(lat, lon)
        r = cfr.get(
            f"{BASE_URL}/visibility", params={"latitude": lat, "longitude": lon},
            headers=headers, impersonate="chrome", timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("merchants", [])

    def get_product_at_merchant(
        self, product_id: str, merchant_id: str, lat: float, lon: float,
        location_name: str, pincode: str, query: str = "",
    ) -> ProductSnapshot | None:
        """Checks one specific product's stock at one specific (non-default) store.

        Unlike the search endpoint, the product-detail endpoint DOES honor an
        explicit merchant_id override - this is the only way to check a secondary
        store's stock for a known product, since you can't "search" a non-default
        store's full catalog directly.
        """
        headers = self._headers(lat, lon)
        headers["merchant_id"] = str(merchant_id)
        r = cfr.post(
            f"{BASE_URL}/v1/layout/product/{product_id}", params={"merchant_id": merchant_id},
            headers=headers, json={}, impersonate="chrome", timeout=self.timeout,
        )
        if r.status_code == 429:
            # Deliberately raised, not returned as None - a rate-limited request
            # must never be confused with a genuine "this store doesn't carry the
            # product" result by callers.
            raise RateLimitedError(f"Blinkit rate-limited checking product {product_id} at merchant {merchant_id}")
        r.raise_for_status()
        payload = r.json()
        if not payload.get("is_success"):
            return None

        # The product-detail response is a nested widget tree. The authoritative
        # `is_sold_out` flag lives as a sibling of (not inside) the cart_item, on
        # the enclosing snippet's `data` dict - same pattern as the search endpoint.
        # Guessing sold-out from price==0 is unreliable (a product can have
        # inventory 0 with a nonzero price still shown), so pair each cart_item
        # with the is_sold_out flag from its own containing dict, not a global guess.
        def _find_cart_item(obj, pid):
            if isinstance(obj, dict):
                ci = obj.get("cart_item")
                if isinstance(ci, dict) and str(ci.get("product_id")) == str(pid):
                    return ci
                for v in obj.values():
                    found = _find_cart_item(v, pid)
                    if found:
                        return found
            elif isinstance(obj, list):
                for v in obj:
                    found = _find_cart_item(v, pid)
                    if found:
                        return found
            return None

        def _walk(obj):
            if isinstance(obj, dict):
                if "is_sold_out" in obj:
                    ci = _find_cart_item(obj, product_id)
                    if ci:
                        yield obj.get("is_sold_out"), ci
                for v in obj.values():
                    yield from _walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from _walk(v)

        matches = list(_walk(payload))
        if not matches:
            return None
        is_sold_out_flag, ci = matches[0]
        return ProductSnapshot(
            platform=self.platform,
            location_name=location_name,
            pincode=pincode,
            merchant_id=str(merchant_id),
            query=query,
            product_id=str(ci.get("product_id", "")),
            brand=ci.get("brand") or "Unknown",
            name=ci.get("display_name") or ci.get("product_name", ""),
            unit=ci.get("unit", ""),
            price=float(ci.get("price") or 0),
            mrp=float(ci.get("mrp") or 0),
            inventory=int(ci.get("inventory", 0) or 0),
            is_sold_out=bool(is_sold_out_flag),
        )

    def _parse_products(self, payload: dict, location_name: str, pincode: str, query: str) -> List[ProductSnapshot]:
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

    def search(
        self, query: str, lat: float, lon: float, location_name: str, pincode: str, max_pages: int = 5,
    ) -> List[ProductSnapshot]:
        """Run a search query at a given lat/lon and return normalized product snapshots.

        Paginates through up to `max_pages` pages (Blinkit returns results ~12 at a
        time across ALL brands for that query, not just the one you care about - a
        single unpaginated request badly undercounts a brand's actual catalog size,
        since most of its SKUs land on page 2+ rather than page 1).
        """
        headers = self._headers(lat, lon)
        base_body = {
            "applied_filters": None,
            "sort": None,
            "postback_meta": {},
            "previous_search_query": "",
            "vertical_cards_processed": [],
        }

        all_snapshots: List[ProductSnapshot] = []
        seen_product_ids: set[str] = set()
        total_so_far = 0

        for page_index in range(max_pages):
            if page_index > 0:
                time.sleep(0.6)  # pagination fires several requests back to back - avoid tripping rate limits

            if page_index == 0:
                params = {"q": query, "search_type": "type_to_search"}
            else:
                params = {
                    "q": query, "offset": page_index * self.PAGE_SIZE, "limit": self.PAGE_SIZE,
                    "actual_query": query, "page_index": page_index, "search_count": total_so_far,
                    "search_method": "basic", "search_type": "type_to_search",
                }
            r = cfr.post(
                f"{BASE_URL}/v1/layout/search", params=params, headers=headers, json=base_body,
                impersonate="chrome", timeout=self.timeout,
            )
            if r.status_code == 429:
                logger.warning("Blinkit rate-limited us on %r page %d - stopping pagination here, keeping what we have", query, page_index)
                break
            r.raise_for_status()
            payload = r.json()
            if not payload.get("is_success"):
                if page_index == 0:
                    logger.warning("Blinkit search for %r returned is_success=false", query)
                break

            page_snapshots = self._parse_products(payload, location_name, pincode, query)
            new_snapshots = [s for s in page_snapshots if s.product_id not in seen_product_ids]
            if not new_snapshots:
                break  # no new products on this page - reached the end of results
            seen_product_ids.update(s.product_id for s in new_snapshots)
            all_snapshots.extend(new_snapshots)
            total_so_far += len(page_snapshots)

            if len(page_snapshots) < self.PAGE_SIZE:
                break  # short page - last page of results

        return all_snapshots
