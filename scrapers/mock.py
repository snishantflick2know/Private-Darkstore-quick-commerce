"""Synthetic scraper used to stand in for platforms we haven't reverse-engineered
yet (Zepto, Instamart) and to backfill plausible historical trend data for the demo.

Every row produced here has `is_synthetic=True` so the dashboard can label it clearly
and never confuse it with real Blinkit data.
"""
from __future__ import annotations

import hashlib
import random
from typing import List

from .base import ProductSnapshot

NAMKEEN_CATALOG = [
    ("Haldiram's", "Haldiram's Aloo Bhujia", "200 g", 60),
    ("Haldiram's", "Haldiram's Moong Dal", "200 g", 65),
    ("Haldiram's", "Haldiram's Golden Mixture Namkeen", "750 g", 299),
    ("Bikaji", "Bikaji Bhujia Sev", "200 g", 58),
    ("Bikaji", "Bikaji Punjabi Tadka", "200 g", 60),
    ("Balaji", "Balaji Wafers Chatpata", "150 g", 40),
    ("Balaji", "Balaji Tikha Mixture", "200 g", 55),
    ("Prataap Snacks", "Yellow Diamond Moong Dal", "200 g", 50),
    ("DFM Foods", "Crax Corn Rings", "80 g", 20),
]


def _stable_seed(*parts: str) -> random.Random:
    key = "|".join(parts).encode()
    seed = int(hashlib.sha256(key).hexdigest(), 16) % (2**32)
    return random.Random(seed)


class MockScraper:
    """Deterministic-per-(platform, location, day) synthetic data generator."""

    def __init__(self, platform: str):
        self.platform = platform

    def search(self, query: str, lat: float, lon: float, location_name: str, pincode: str) -> List[ProductSnapshot]:
        rng = _stable_seed(self.platform, location_name, query)
        snapshots = []
        for brand, name, unit, mrp in NAMKEEN_CATALOG:
            if query.lower() not in name.lower() and query.lower() not in brand.lower() and query.lower() != "namkeen":
                continue
            inventory = rng.choice([0, 0, 2, 5, 8, 12, 20, 35])
            discount = rng.choice([0, 0, 5, 10, 15])
            price = round(mrp * (1 - discount / 100), 2)
            snapshots.append(
                ProductSnapshot(
                    platform=self.platform,
                    location_name=location_name,
                    pincode=pincode,
                    merchant_id=f"mock-{self.platform}-{pincode}",
                    query=query,
                    product_id=f"mock-{abs(hash((brand, name, unit)))}",
                    brand=brand,
                    name=name,
                    unit=unit,
                    price=price,
                    mrp=mrp,
                    inventory=inventory,
                    is_sold_out=inventory == 0,
                    is_synthetic=True,
                )
            )
        return snapshots
