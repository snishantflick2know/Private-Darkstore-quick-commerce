"""Verifies that each configured GURGAON_LOCATIONS point resolves to a distinct
Blinkit dark store (merchant_id). Run this whenever you add/move a location,
to catch accidental double-counting of the same physical warehouse as if it
were two independent catchments.

Usage: python scripts/check_store_overlap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.blinkit import BlinkitScraper, BASE_URL
from curl_cffi import requests as cfr

from config import GURGAON_LOCATIONS


def main() -> None:
    scraper = BlinkitScraper()
    seen: dict[str, str] = {}
    had_overlap = False

    for loc in GURGAON_LOCATIONS:
        headers = scraper._headers(loc["lat"], loc["lon"])
        r = cfr.get(
            f"{BASE_URL}/visibility",
            params={"latitude": loc["lat"], "longitude": loc["lon"]},
            headers=headers, impersonate="chrome", timeout=15,
        )
        merchants = r.json().get("merchants", [])
        mid = merchants[0]["id"] if merchants else None
        if mid in seen:
            print(f'⚠️  "{loc["name"]}" shares a Blinkit dark store (merchant_id {mid}) with "{seen[mid]}"')
            had_overlap = True
        else:
            print(f'✅ "{loc["name"]}" -> distinct merchant_id {mid}')
        if mid:
            seen[mid] = loc["name"]

    if not had_overlap:
        print("\nAll configured locations map to distinct Blinkit dark stores.")


if __name__ == "__main__":
    main()
