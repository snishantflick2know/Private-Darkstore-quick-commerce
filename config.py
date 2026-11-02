"""Static configuration: locations to poll and search queries to run.

Scope note: Blinkit-only (Zepto/Instamart dropped to keep this live/free/fast -
Blinkit costs nothing and has no per-request budget to manage, unlike the
Apify-backed platforms). The scraper modules for Zepto/Instamart still exist
under scrapers/ if you want to bring them back later.
"""
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent

# Pincode is informational (used for labeling/grouping); lat/lon is what
# actually drives which Blinkit dark store answers the query. Despite the name
# (kept for backward compat with existing code/scripts), this now spans two
# cities - Sohna Road (Gurgaon, merchant_id 36048) and Lajpat Nagar (Delhi,
# merchant_id 35554), both verified via Blinkit's /visibility endpoint.
GURGAON_LOCATIONS = [
    {"name": "Sohna Road", "pincode": "122018", "lat": 28.4089, "lon": 77.0372, "city": "Gurgaon"},
    {"name": "Lajpat Nagar", "pincode": "110024", "lat": 28.5677, "lon": 77.2433, "city": "Delhi"},
]

# Search queries run per location. Verified live against Blinkit to maximize
# coverage across all 5 tracked brands below (see brand name note).
SEARCH_QUERIES = ["paper boat", "tropicana", "b natural juice", "raw pressery"]

# Brands tracked for competitive benchmarking. NOTE: these must match the brand
# name actually printed on the product listing, not the parent company name.
# Verified live via Blinkit search (e.g. "paper boat", "juice", "tropicana")
# before committing to these exact strings.
TRACKED_BRANDS = [
    "Paper Boat",  # Hector Beverages
    "B Natural",  # ITC
    "Real",  # Dabur
    "Tropicana",  # PepsiCo
    "Raw Pressery",
]

CLIENT_BRAND = "Paper Boat"

# Parent company label per brand - purely cosmetic (shown under the brand name
# in the web dashboard's nav), not used for any matching/scraping logic.
BRAND_COMPANIES = {
    "Paper Boat": "Hector Beverages",
    "B Natural": "ITC",
    "Real": "Dabur",
    "Tropicana": "PepsiCo",
    "Raw Pressery": "Rakyan Beverages",
}

CATEGORY_LABEL = "Juices"  # cosmetic label for the web dashboard's filter chip

# Absolute, anchored to this file's location - NOT relative to the process's
# current working directory. This matters because collector.py gets imported
# from webapp/server.py, whose cwd is webapp/, not the project root; a
# relative path there would silently create/write a second, different SQLite
# file instead of the real one (exactly this bug happened once - see git
# history / AGENTS.md if curious).
DB_PATH = str(_PROJECT_ROOT / "data" / "stock_tracker.db")
AUTO_REFRESH_MINUTES = 10  # shared by both the Streamlit app and the web dashboard

# Experimental: multi-store "sector" coverage. A single point can be served by
# several real dark stores with independent stock (confirmed: Sector 49 alone
# has 4 candidate Blinkit stores). For a sector here, we discover ALL serving
# stores (not just the nearest) and check tracked-brand stock at each one when
# the nearest store is sold out. Kept to a small list while validating the
# approach - see scripts/test_multistore.py.
TEST_SECTORS = [
    {"name": "Sector 49, Sohna Road", "pincode": "122018", "lat": 28.4058, "lon": 77.0655},
]
