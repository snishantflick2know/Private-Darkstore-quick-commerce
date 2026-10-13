"""Static configuration: locations to poll and search queries to run."""

# A spread of Gurgaon localities/dark-store catchments. Pincode is informational
# (used for labeling/grouping); lat/lon is what actually drives which dark store
# answers the query.
#
# Verified (via Blinkit's /visibility endpoint) that each of these 5 points
# resolves to a DISTINCT merchant_id/dark store - i.e. no two "locations" here
# are secretly the same physical warehouse. The original "Sector 14" point was
# dropped because it shared a dark store with "DLF Cyber City" (merchant_id
# 43483 for both); "MG Road" was swapped in instead after confirming it maps to
# a different store (47108). Re-verify with scripts/check_store_overlap.py
# whenever you add or move a location.
GURGAON_LOCATIONS = [
    {"name": "DLF Cyber City", "pincode": "122002", "lat": 28.4595, "lon": 77.0266},
    {"name": "MG Road", "pincode": "122002", "lat": 28.4769, "lon": 77.0881},
    {"name": "Sohna Road", "pincode": "122018", "lat": 28.4089, "lon": 77.0372},
    {"name": "Sector 56", "pincode": "122011", "lat": 28.4111, "lon": 77.0912},
    {"name": "Golf Course Road", "pincode": "122002", "lat": 28.4421, "lon": 77.1025},
]

# Search queries run per location. Keep generic enough to surface Haldiram's +
# competitor namkeen SKUs in one pass.
SEARCH_QUERIES = ["haldiram namkeen", "namkeen", "bhujia"]

# Zepto/Instamart go through paid-per-result Apify actors (~$1.30-5 per 1,000
# results), unlike Blinkit which is free. Keep this list short to control cost;
# "namkeen" alone surfaces Haldiram's + all competitor namkeen SKUs in one query.
APIFY_SEARCH_QUERIES = ["namkeen"]

# Apify actor IDs used for Zepto/Instamart. Swap these out if you prefer a
# different actor from the Apify Store - any actor is fine as long as the
# corresponding scraper class maps its output fields correctly.
ZEPTO_ACTOR_ID = "solidcode/zepto-scraper"
INSTAMART_ACTOR_ID = "solidcode/swiggy-scraper"

# Brands tracked for competitive benchmarking. NOTE: these must match the brand
# name actually printed on the product listing, not the parent company name -
# e.g. Prataap Snacks' namkeen brand is "Yellow Diamond" and DFM Foods' is
# "Crax"; the product data never says "Prataap Snacks" or "DFM Foods" anywhere,
# so using the company name here silently matches zero rows.
TRACKED_BRANDS = [
    "Haldiram's",
    "Bikaji",
    "Balaji",
    "Yellow Diamond",  # Prataap Snacks
    "Crax",  # DFM Foods
]

CLIENT_BRAND = "Haldiram's"

DB_PATH = "data/stock_tracker.db"
