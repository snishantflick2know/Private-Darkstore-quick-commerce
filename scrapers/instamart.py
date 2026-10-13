"""Swiggy Instamart scraper via an Apify Store actor.

Instamart's own web API sits behind an AWS WAF JS challenge (verified by testing -
see README.md), which is a much harder bar than Blinkit's TLS-fingerprint-only
check. Going through a third-party Apify actor (`solidcode/swiggy-scraper` by
default) sidesteps that.

Note: `smacient/swiggy-instamart-data-extractor` looked like a better fit (cheaper,
higher rated) but requires approving "full account access" permissions in the
Apify console before it can run - see the error message if you want to switch to
it instead. `solidcode/swiggy-scraper` works without that approval step.

Cost: ~$4 per 1,000 results (billed to your Apify account, see scrapers/apify_base.py).

Note: this actor only exposes an `inStock` boolean, not an exact inventory count
(unlike Blinkit/Zepto), so `inventory` here is a coarse 1/0 stand-in, not a real count.
"""
from __future__ import annotations

import logging
from typing import List

from .apify_base import get_apify_client
from .base import ProductSnapshot

logger = logging.getLogger(__name__)

DEFAULT_ACTOR_ID = "solidcode/swiggy-scraper"


class InstamartScraper:
    platform = "instamart"

    def __init__(self, actor_id: str = DEFAULT_ACTOR_ID, max_results: int = 20, city: str = "Gurgaon"):
        self.actor_id = actor_id
        self.max_results = max_results
        self.city = city

    def search(self, query: str, lat: float, lon: float, location_name: str, pincode: str) -> List[ProductSnapshot]:
        client = get_apify_client()
        run_input = {
            "searchQueries": [query],
            "city": self.city,
            "area": location_name,
            "maxResults": self.max_results,
        }
        run = client.actor(self.actor_id).call(run_input=run_input)
        items = list(client.dataset(run.default_dataset_id).iterate_items())

        snapshots = []
        for item in items:
            in_stock = item.get("inStock", True)
            snapshots.append(
                ProductSnapshot(
                    platform=self.platform,
                    location_name=location_name,
                    pincode=pincode,
                    merchant_id="",  # not exposed by this actor
                    query=query,
                    product_id=str(item.get("productId") or f"{item.get('name', '')}|{item.get('quantity', '')}"),
                    brand=item.get("brand") or "Unknown",
                    name=item.get("name", ""),
                    unit=item.get("quantity", ""),
                    price=float(item.get("price") or 0),
                    mrp=float(item.get("mrp") or 0),
                    inventory=1 if in_stock else 0,
                    is_sold_out=not bool(in_stock),
                    is_synthetic=False,
                )
            )
        return snapshots
