"""Polls configured platforms/locations/queries and stores snapshots.

Run this on a schedule (cron, launchd, APScheduler, etc.) to build real stock
history over time. Each run is one "snapshot" of current availability.

Blinkit is free (direct API). Zepto/Instamart go through paid Apify actors
(~$1.30-5 per 1,000 results) when APIFY_API_TOKEN is set in .env - otherwise
they fall back to synthetic mock data so the pipeline still runs end-to-end.

Usage:
    python collector.py                  # Blinkit (live) + Zepto/Instamart (live if token set, else mock)
    python collector.py --mock-only      # Force mock data for Zepto/Instamart even if token is set (free, no Apify cost)
    python collector.py --blinkit-only   # Skip Zepto/Instamart entirely
"""
from __future__ import annotations

import argparse
import logging
import os
import time

from dotenv import load_dotenv

from config import APIFY_SEARCH_QUERIES, DB_PATH, GURGAON_LOCATIONS, SEARCH_QUERIES
from scrapers.blinkit import BlinkitScraper
from scrapers.mock import MockScraper
from storage.db import init_db, save_snapshots

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _build_scraper_plan(include_others: bool, mock_only: bool):
    """Returns a list of (scraper, queries) pairs. Blinkit always gets the full
    query list (free); Zepto/Instamart get the shorter, cost-controlled list.
    """
    plan = [(BlinkitScraper(), SEARCH_QUERIES)]
    if not include_others:
        return plan

    have_token = bool(os.environ.get("APIFY_API_TOKEN")) and not mock_only
    if have_token:
        from scrapers.instamart import InstamartScraper
        from scrapers.zepto import ZeptoScraper

        plan.append((ZeptoScraper(), APIFY_SEARCH_QUERIES))
        plan.append((InstamartScraper(), APIFY_SEARCH_QUERIES))
        logger.info("APIFY_API_TOKEN found - using live Zepto/Instamart actors (paid per result).")
    else:
        plan.append((MockScraper("zepto"), APIFY_SEARCH_QUERIES))
        plan.append((MockScraper("instamart"), APIFY_SEARCH_QUERIES))
        logger.info("No APIFY_API_TOKEN (or --mock-only set) - using simulated Zepto/Instamart data.")
    return plan


def run_once(include_others: bool = True, mock_only: bool = False) -> int:
    init_db(DB_PATH)
    plan = _build_scraper_plan(include_others, mock_only)

    total = 0
    for scraper, queries in plan:
        for loc in GURGAON_LOCATIONS:
            for query in queries:
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
                time.sleep(0.5)  # be polite / avoid rate limiting
    logger.info("Done. %d snapshot rows saved.", total)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--blinkit-only", action="store_true", help="Skip Zepto/Instamart entirely")
    parser.add_argument("--mock-only", action="store_true", help="Force mock Zepto/Instamart data even if APIFY_API_TOKEN is set (avoids Apify cost)")
    args = parser.parse_args()
    run_once(include_others=not args.blinkit_only, mock_only=args.mock_only)
