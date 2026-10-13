"""Shared interfaces for quick-commerce stock scrapers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Protocol


@dataclass
class ProductSnapshot:
    """A single observation of one SKU at one dark store, at one point in time."""

    platform: str          # "blinkit", "zepto", "instamart"
    location_name: str     # human label, e.g. "Gurgaon - DLF Cyber City"
    pincode: str
    merchant_id: str
    query: str              # the search term that surfaced this product
    product_id: str
    brand: str
    name: str
    unit: str
    price: float
    mrp: float
    inventory: int
    is_sold_out: bool
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_synthetic: bool = False  # True for seeded demo/history rows, False for live-scraped rows


class StockScraper(Protocol):
    """Interface every platform-specific scraper must implement."""

    platform: str

    def search(self, query: str, lat: float, lon: float, location_name: str, pincode: str) -> List[ProductSnapshot]:
        ...
