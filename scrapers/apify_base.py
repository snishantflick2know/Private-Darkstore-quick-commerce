"""Shared Apify client setup for scrapers that go through Apify Store actors
instead of a direct reverse-engineered API (currently Zepto and Instamart).

Requires APIFY_API_TOKEN in the environment or a .env file at the project root.
These actors are paid per result (not covered by the free Blinkit path), billed
against your Apify account balance (free plan: $5/month, no card required).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

_client = None


def get_apify_client():
    global _client
    if _client is None:
        from apify_client import ApifyClient

        token = os.environ.get("APIFY_API_TOKEN")
        if not token:
            raise RuntimeError(
                "APIFY_API_TOKEN not set. Add it to a .env file at the project root "
                "(see README) to enable live Zepto/Instamart data."
            )
        _client = ApifyClient(token)
    return _client
