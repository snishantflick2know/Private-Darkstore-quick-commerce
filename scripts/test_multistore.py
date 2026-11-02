"""Validates the multi-store "sector" coverage approach before wiring it into the
main collector/dashboard.

For each sector in config.TEST_SECTORS:
  1. Run the normal paginated search at the nearest (rank-1) store to discover
     the tracked-brand product catalog there.
  2. Discover all OTHER dark stores that also serve this point.
  3. For any tracked-brand product that's sold out OR low-stock at the nearest
     store, check its stock at each secondary store too (this is the case that
     actually matters for the business question "is it really unavailable/low
     nearby, or just at the closest store" - a real example we found: Haldiram's
     Kachori showed 1 unit at the nearest store but 6 at a secondary one, neither
     technically "sold out").

Usage: python scripts/test_multistore.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CLIENT_BRAND, SEARCH_QUERIES, TEST_SECTORS
from scrapers.blinkit import BlinkitScraper, RateLimitedError

LOW_STOCK_THRESHOLD = 5  # units or fewer at the primary store triggers a secondary-store check
SECONDARY_CHECK_DELAY = 1.0  # seconds between secondary-store requests, to avoid rate limiting


def main() -> None:
    scraper = BlinkitScraper()

    for sector in TEST_SECTORS:
        print(f"\n{'=' * 70}\nSECTOR: {sector['name']}  ({sector['lat']}, {sector['lon']})\n{'=' * 70}")

        merchants = scraper.get_merchants(sector["lat"], sector["lon"])
        print(f"Dark stores serving this point: {len(merchants)}")
        for m in merchants:
            print(f"  - merchant {m['id']} (rank {m.get('rank')})")
        if not merchants:
            continue
        primary_merchant_id = str(merchants[0]["id"])
        secondary_merchants = [m for m in merchants[1:]]

        # Step 1: discover CLIENT_BRAND (Haldiram's) products at the primary (nearest)
        # store. Scoped to just the client brand for this test - cross-checking
        # every tracked competitor too multiplies request volume and triggers
        # rate limiting badly (confirmed in an earlier run).
        tracked_products = {}  # product_id -> snapshot
        for query in SEARCH_QUERIES:
            results = scraper.search(query, sector["lat"], sector["lon"], sector["name"], sector["pincode"])
            for snap in results:
                if snap.brand == CLIENT_BRAND:
                    tracked_products[snap.product_id] = snap

        print(f"\n{CLIENT_BRAND} products found at primary store (merchant {primary_merchant_id}): {len(tracked_products)}")
        flagged = [
            s for s in tracked_products.values()
            if s.is_sold_out or s.inventory <= LOW_STOCK_THRESHOLD
        ]
        print(f"Of those, sold out or low-stock (<={LOW_STOCK_THRESHOLD} units) at the primary store: {len(flagged)}")

        if not flagged or not secondary_merchants:
            print("Nothing to cross-check at secondary stores.")
            continue

        # Step 2: for sold-out/low-stock products only, check secondary stores.
        print(f"\nCross-checking {len(flagged)} flagged product(s) against {len(secondary_merchants)} secondary store(s)...")
        for snap in flagged:
            print(f"\n  {snap.brand} - {snap.name} ({snap.unit}) [product_id={snap.product_id}]")
            status = "SOLD OUT" if snap.is_sold_out else f"LOW STOCK ({snap.inventory} units)"
            print(f"    Primary store {primary_merchant_id}: {status}")
            for m in secondary_merchants:
                time.sleep(SECONDARY_CHECK_DELAY)
                try:
                    alt = scraper.get_product_at_merchant(
                        snap.product_id, m["id"], sector["lat"], sector["lon"], sector["name"], sector["pincode"],
                    )
                except RateLimitedError:
                    print(f"    Store {m['id']} (rank {m.get('rank')}): ⚠️ check failed (rate limited) - inconclusive, NOT the same as 'not carried'")
                    continue
                if alt is None:
                    print(f"    Store {m['id']} (rank {m.get('rank')}): doesn't carry this product")
                elif alt.is_sold_out:
                    print(f"    Store {m['id']} (rank {m.get('rank')}): also sold out")
                else:
                    print(f"    Store {m['id']} (rank {m.get('rank')}): ✅ IN STOCK - {alt.inventory} units")


if __name__ == "__main__":
    main()
