"""Backfills synthetic historical snapshots so the dashboard has trend data to show
on day one, before the real collector has had time to accumulate history.

Every row this script inserts has is_synthetic=True and is clearly labeled as such
in the dashboard. It does NOT touch/replace any real Blinkit data already collected.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from config import DB_PATH, GURGAON_LOCATIONS, SEARCH_QUERIES
from scrapers.base import ProductSnapshot
from scrapers.mock import NAMKEEN_CATALOG, _stable_seed
from storage.db import init_db, save_snapshots


def seed(days: int = 7, points_per_day: int = 4) -> int:
    init_db(DB_PATH)
    now = datetime.now(timezone.utc)
    total = 0

    for loc in GURGAON_LOCATIONS:
        for query in SEARCH_QUERIES:
            for platform in ["blinkit", "zepto", "instamart"]:
                rng = _stable_seed(platform, loc["name"], query, "history")
                # per-product inventory "walk" so trends look like real depletion/restock cycles
                state = {name: rng.choice([30, 25, 40, 15]) for _, name, _, _ in NAMKEEN_CATALOG}
                batch = []
                for day in range(days, 0, -1):
                    for p in range(points_per_day):
                        ts = now - timedelta(days=day, hours=(24 / points_per_day) * p)
                        for brand, name, unit, mrp in NAMKEEN_CATALOG:
                            if query.lower() not in name.lower() and query.lower() not in brand.lower() and query.lower() != "namkeen":
                                continue
                            # simulate depletion with occasional restock
                            drop = rng.choice([0, 1, 2, 3, 5])
                            state[name] = max(0, state[name] - drop)
                            if state[name] == 0 and rng.random() < 0.6:
                                state[name] = rng.choice([20, 30, 40])  # restock
                            inv = state[name]
                            discount = rng.choice([0, 0, 5, 10])
                            price = round(mrp * (1 - discount / 100), 2)
                            batch.append(
                                ProductSnapshot(
                                    platform=platform,
                                    location_name=loc["name"],
                                    pincode=loc["pincode"],
                                    merchant_id=f"hist-{platform}-{loc['pincode']}",
                                    query=query,
                                    product_id=f"hist-{abs(hash((brand, name, unit)))}",
                                    brand=brand,
                                    name=name,
                                    unit=unit,
                                    price=price,
                                    mrp=mrp,
                                    inventory=inv,
                                    is_sold_out=inv == 0,
                                    fetched_at=ts.isoformat(),
                                    is_synthetic=True,
                                )
                            )
                total += save_snapshots(DB_PATH, batch)
    return total


if __name__ == "__main__":
    n = seed()
    print(f"Seeded {n} synthetic historical snapshot rows.")
