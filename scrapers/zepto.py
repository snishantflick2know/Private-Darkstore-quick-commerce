"""Zepto scraper via an Apify Store actor.

Zepto's own API requires a rotating per-session request signature (not replayable
cold like Blinkit's), and its web app blocks headless browsers outright - see
`README.md` for what we tried. Going through a third-party Apify actor
(`solidcode/zepto-scraper` by default) sidesteps that: they've already solved the
anti-bot problem, and we pay per result instead of maintaining our own bypass.

Cost: ~$1.30 per 1,000 results (billed to your Apify account, see scrapers/apify_base.py).
"""
from __future__ import annotations

import logging
from typing import List

from .apify_base import get_apify_client
from .base import ProductSnapshot

logger = logging.getLogger(__name__)

DEFAULT_ACTOR_ID = "solidcode/zepto-scraper"


class ZeptoScraper:
    platform = "zepto"

    def __init__(self, actor_id: str = DEFAULT_ACTOR_ID, max_results: int = 20):
        self.actor_id = actor_id
        self.max_results = max_results

    def search(self, query: str, lat: float, lon: float, location_name: str, pincode: str) -> List[ProductSnapshot]:
        client = get_apify_client()
        run_input = {
            "searchTerms": [query],
            "city": "custom",
            "latitude": str(lat),
            "longitude": str(lon),
            "maxResults": self.max_results,
        }
        run = client.actor(self.actor_id).call(run_input=run_input)
        items = list(client.dataset(run.default_dataset_id).iterate_items())

        snapshots = []
        for item in items:
            in_stock = item.get("inStock")
            snapshots.append(
                ProductSnapshot(
                    platform=self.platform,
                    location_name=location_name,
                    pincode=pincode,
                    merchant_id=str(item.get("storeId", "")),
                    query=query,
                    product_id=str(item.get("productId") or item.get("skuId") or ""),
                    brand=item.get("brand") or "Unknown",
                    name=item.get("name", ""),
                    unit=item.get("packSize", ""),
                    price=float(item.get("price") or 0),
                    mrp=float(item.get("mrp") or 0),
                    inventory=int(item.get("inventoryAvailable") or 0),
                    is_sold_out=not bool(in_stock) if in_stock is not None else False,
                    is_synthetic=False,
                )
            )
        return snapshots
