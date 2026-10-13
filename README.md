# Namkeen Stock Intelligence — Gurgaon (Haldiram's pitch prototype)

A working prototype that tracks quick-commerce shelf availability for Haldiram's
namkeen vs. competitors (Bikaji, Balaji, Prataap Snacks, DFM Foods) across Gurgaon
dark stores, and surfaces:

- **Out-of-stock alerts** — what's sold out right now, where
- **Competitive benchmarking** — availability % by brand, by platform
- **Stock-out frequency/duration** — how often and how long SKUs go OOS
- **Depletion forecast** — estimated time-to-stockout from inventory decline velocity

## What's real vs. simulated

- **Blinkit: real, live.** `scrapers/blinkit.py` calls Blinkit's actual search API
  (no login needed) for 5 Gurgaon localities and returns live price/MRP/inventory/
  sold-out data per SKU per dark store.
- **Zepto & Instamart: simulated.** `scrapers/mock.py` generates plausible stand-in
  data so the dashboard can demo multi-platform comparison. Their real APIs need
  separate reverse-engineering (notes on how, in `scrapers/zepto.py` /
  `scrapers/instamart.py` docstrings) — app-only clients, harder than Blinkit's web client.
- **Historical trend data is seeded synthetically** (`seed_history.py`) so charts
  aren't empty on day one. Every simulated/seeded row is flagged `is_synthetic=True`
  and labeled as such in the dashboard. Real trend data accumulates once
  `collector.py` is run on a schedule.

## ⚠️ Important before pitching as production-ready

The Blinkit integration works by reverse-engineering their internal consumer-web
API (bypassing Cloudflare bot detection via TLS fingerprint impersonation). This is
**not an officially sanctioned data feed** and is against Blinkit's Terms of
Service. It's fine for demoing feasibility, but for an actual commercial deployment
you should:
- License data from an existing data-aggregation vendor (several already do this
  legally/commercially — e.g. Apify/Upscrape-style scraping-as-a-service actors), or
- Negotiate direct API/data-sharing access with each platform, or
- Accept the operational risk (breakage, IP blocks, legal exposure) explicitly as
  a known trade-off if going down the self-hosted scraping route.

## Setup

```bash
cd haldiram_oos_tracker
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # or: requests streamlit pandas plotly curl_cffi
```

## Usage

```bash
# 1. One-time: seed synthetic historical trend data for the demo
python seed_history.py

# 2. Pull live Blinkit data (+ simulated Zepto/Instamart) for Gurgaon
python collector.py
# Blinkit only: python collector.py --no-mock

# 3. Launch the dashboard
streamlit run app/dashboard.py
```

For real trend/depletion data over time, schedule `collector.py` to run every
15-30 min (cron/launchd/APScheduler).

## Architecture

```
scrapers/        platform-specific stock scrapers (BlinkitScraper is real; Zepto/
                 Instamart stubs + MockScraper for demo)
storage/db.py    SQLite time-series store (one row per product observation)
analytics/       OOS alerts, availability benchmarking, stockout duration,
                 depletion forecasting
collector.py     polls all configured locations/queries, saves snapshots
seed_history.py  backfills synthetic history for demo purposes
app/dashboard.py Streamlit UI
config.py        Gurgaon locations, tracked brands, search queries
```

## Extending to a new platform

Implement a class with the same `search(query, lat, lon, location_name, pincode)`
signature as `BlinkitScraper` (see `scrapers/base.py` for the `ProductSnapshot`
shape), and add it to `collector.py`. No other code needs to change.

## Extending to a new city

Add entries to `GURGAON_LOCATIONS` in `config.py` (or rename/generalize into
`LOCATIONS`) with `name`, `pincode`, `lat`, `lon`.
