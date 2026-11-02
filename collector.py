"""Polls Blinkit (free, live API) and stores snapshots.

Run this on a schedule (cron, launchd, APScheduler, etc.) to build real stock
history over time. Each run is one "snapshot" of current availability.

Scope note: Zepto/Instamart dropped for now (they went through paid Apify
actors) to keep this entirely free and simple while focused on Sohna Road
only - see scrapers/zepto.py and scrapers/instamart.py if you want them back.

Usage:
    python collector.py
"""
from __future__ import annotations

import logging
import time

from config import DB_PATH, GURGAON_LOCATIONS, SEARCH_QUERIES, SNAPSHOT_RETENTION_DAYS
from scrapers.blinkit import BlinkitScraper
from storage.db import init_db, prune_old_snapshots, save_snapshots

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_once() -> int:
    init_db(DB_PATH)
    scraper = BlinkitScraper()

    total = 0
    for loc in GURGAON_LOCATIONS:
        for query in SEARCH_QUERIES:
            try:
                snaps = scraper.search(
                    query=query, lat=loc["lat"], lon=loc["lon"],
                    location_name=loc["name"], pincode=loc["pincode"],
                )
            except Exception as exc:  # keep polling other combos on failure
                logger.warning("%s search failed for %s/%s: %s", scraper.platform, loc["name"], query, exc)
                continue
            saved = save_snapshots(DB_PATH, snaps)
            total += saved
            logger.info("%s | %s | %r -> %d products", scraper.platform, loc["name"], query, saved)
            time.sleep(1.2)  # be polite / avoid rate limiting - each query paginates internally too
    logger.info("Done. %d snapshot rows saved.", total)

    pruned = prune_old_snapshots(DB_PATH, days=SNAPSHOT_RETENTION_DAYS)
    if pruned:
        logger.info("Pruned %d snapshot rows older than %d days.", pruned, SNAPSHOT_RETENTION_DAYS)

    return total


if __name__ == "__main__":
    run_once()
