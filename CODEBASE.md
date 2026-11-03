# Shelf Pulse — how to read this codebase

A quick-commerce stock-availability tracker for FMCG brands. It scrapes Blinkit
every hour (or on demand), stores every observation in SQLite, and turns the
history into a pitch-ready dashboard: availability vs. competitors, stock-out
windows, depletion forecasts, share gaps, and raw metadata.

**Start here:** the data pipeline is the whole product. Everything else is
presentation. Read `collector.py` → `scrapers/blinkit.py` → `storage/db.py` →
`analytics/metrics.py` → `webapp/server.py` in that order and you'll understand
~90% of it.

---

## 1. Architecture at a glance

```
Blinkit API ──► scrapers/blinkit.py ──► collector.py ──► data/stock_tracker.db
   (unofficial consumer-web API, curl_cffi Chrome impersonation)   (SQLite, append-only)
                                                                      │
                                              analytics/metrics.py ◄──┘
                                              (pandas rollups)
                                                      │
                    ┌─────────────────────────────────┼───────────────────────────┐
                    ▼                                 ▼                           ▼
            webapp/server.py                 app/dashboard.py            scripts/export_static_site.py
            (FastAPI /api/dashboard)         (legacy Streamlit UI)       (scheduled job: scrape + bake JSON)
                    │                                                                 │
            docs/ (static frontend) ◄──────────── docs/data/*.json ◄──────────────────┘
            plain HTML/CSS/JS, no build          committed to git,
            served by FastAPI locally            served by GitHub Pages
            or by GitHub Pages
```

**Two ways to run it:**

- **Local (live backend):** `uvicorn server:app` inside `webapp/` → the frontend
  calls `GET /api/dashboard` and gets data computed on the fly from SQLite. The
  "Refresh live" button triggers a real Blinkit scrape.
- **Static (GitHub Pages):** no server exists, so `docs/data/<brand>.json` files
  are pre-baked by `scripts/export_static_site.py` (which reuses the *same*
  `server.py` payload builder) and committed to the repo. The frontend tries
  `/api/dashboard` first, falls back to the static JSON, then to sample data in
  `docs/js/data.js`.

**Data refresh in practice:** Blinkit blocks datacenter IPs (GitHub Actions
gets HTTP 403 on every query — see run logs), so real scrapes only work from a
residential IP. `refresh.command` is the supported path: double-click / run it
on a Mac → scrape → regenerate JSON → commit → push. `cron-job.org` still fires
the GitHub Actions workflow hourly; those runs now skip the export when they
scrape 0 rows (which is all of them) instead of making empty churn commits.

---

## 2. The single most important concept: the `snapshots` table

`storage/db.py` — one row per product per store **per scrape**, append-only.
Nothing is ever updated; every check just appends ~380 rows. Rows older than
30 days are pruned (`prune_old_snapshots`).

| Column | Meaning |
|---|---|
| `platform` | `blinkit` (only platform wired for real data) |
| `location_name` / `pincode` | configured area (Sohna Road, Lajpat Nagar) |
| `merchant_id` | Blinkit's dark-store ID that served this check |
| `query` | search term that surfaced the product |
| `product_id` / `brand` / `name` / `unit` | what it is |
| `price` / `mrp` / `inventory` | selling price, MRP, units in stock |
| `is_sold_out` | **effective out-of-stock** = Blinkit's flag OR `inventory <= 0` |
| `fetched_at` | ISO-8601 UTC timestamp of the check |
| `is_synthetic` | 1 = seeded demo data, 0 = real scrape |

**`is_sold_out` caveat (important):** Blinkit's *search* endpoint reports
`is_sold_out: false` even for genuinely out-of-stock products (verified against
the product-detail endpoint, which reports the truth). `inventory <= 0` is the
reliable signal — that's why `scrapers/blinkit.py` ORs the two.

A second table, `notifications`, stores generated alerts (stockout / restock /
low_stock / new_sku / delisting) produced by diffing consecutive scrapes in
`analytics/notifications.py`.

**Interval censoring (FMCG logic):** a product seen in stock at 12:00 and out
at 1:00 went out *sometime in that hour* — never report a fake point. Windows
(`current_stockout_window`) and duration ranges (`_out_bounds`) are built on
this, and they tighten automatically as check frequency increases.

---

## 3. File map

### Configuration & entry points

| File | What it does |
|---|---|
| `config.py` | The knobs: `TRACKED_BRANDS`, `CLIENT_BRAND`, `SEARCH_QUERIES`, `GURGAON_LOCATIONS` (lat/lon/pincode), `AUTO_REFRESH_MINUTES`, `SNAPSHOT_RETENTION_DAYS`, brand aliases. Change brands/areas here. |
| `collector.py` | `run_once()`: loops locations × queries → `scraper.search()` → saves snapshots → prunes >30d. The scrape entry point. |
| `refresh.command` | Double-clickable Mac script: runs the export script, commits, `pull --rebase -X theirs` (auto-resolves against remote auto-commits), pushes. The supported "update the site" button. |
| `requirements.txt` | Deps: `curl_cffi`, `pandas`, `fastapi`, `uvicorn`, `streamlit`, etc. |

### Scraping

| File | What it does |
|---|---|
| `scrapers/blinkit.py` | The only live scraper. `search()` paginates `/v1/layout/search` (12/page, up to 5 pages) per location; `_parse_products` normalizes snippets into `ProductSnapshot`. Also `get_merchants()` (all dark stores serving a lat/lon) and `get_product_at_merchant()` (single-product check at a specific store — the product-detail endpoint honors merchant_id, the search endpoint does not). `RateLimitedError` on HTTP 429. |
| `scrapers/base.py` | `ProductSnapshot` dataclass + `BaseScraper` interface. |
| `scrapers/mock.py` | Synthetic-data scraper (used to seed demos / tests). |
| `scrapers/apify_base.py`, `zepto.py`, `instamart.py` | Paid-API experiments — **not wired into the live pipeline** (dropped for cost/latency). Kept for reference. |

### Storage & analytics

| File | What it does |
|---|---|
| `storage/db.py` | SQLite schema (`snapshots`, `notifications`), `save_snapshots`, `load_snapshots`, `latest_snapshot` helpers, `prune_old_snapshots`. |
| `analytics/metrics.py` | All the math. Key functions: `latest_snapshot` / `previous_snapshot` (dedupe to newest row per product), `availability_by_brand` / `availability_by_store_brand` (% in stock), `current_oos_alerts` (out right now), `current_stockout_started_at` / `current_stockout_window` (outage start / honest window), `stockout_duration_hours` (total OOS hours + episode count), `oos_hours_by_daypart` (peak 6–11 PM IST vs off-peak split — `PEAK_*_HOUR_IST` constants at top), `stock_on_shelf_by_brand` (units share), `depletion_forecast` (units/hr velocity → est hours to stockout), `needs_attention`. |
| `analytics/notifications.py` | `generate_notifications(prev_latest, new_latest, ...)`: diffs consecutive scrapes → stockout/restock/low_stock/new_sku/delisting events. |

### Backend

| File | What it does |
|---|---|
| `webapp/server.py` | FastAPI app. `build_dashboard(brand)` is the heart: loads snapshots → runs every metrics function → assembles the exact JSON contract `docs/js/data.js` defines (`meta`, `headline`, `trend`, `tiles`, `stores`, `stockouts`, `comparison`, `forecast`, `alerts`, `products`, `snapshotHistory`, …). Serves `docs/` statically, `GET /api/dashboard`, `POST /api/refresh` (live scrape), `POST /api/nearby` (on-demand nearby-store check — deliberately manual due to rate limits). Display-layer only: all times converted UTC→IST here (`_ist`, `_fmt_window`, `_out_bounds`, `_fmt_dur`, `_in_peak`). |
| `scripts/export_static_site.py` | The scheduled job: `_run_refresh()` (scrape + alert diff) → `build_dashboard()` per brand → writes `docs/data/<brand>.json` + `index.json`. Skips the export entirely when the scrape got 0 rows (the GitHub-403 case). |

### Frontend (`docs/` — plain HTML/CSS/JS ES modules, no build step)

| File | What it does |
|---|---|
| `docs/index.html` | Shell; loads `js/app.js` as a module. |
| `docs/js/app.js` | App state + data loading (API → static JSON → SAMPLE fallback) + one delegated click/input handler for every `data-action`. Add new interactions by adding a `data-action` and a `case` in the switch. |
| `docs/js/data.js` | `SAMPLE` — the fallback payload **and** the de-facto API contract. New backend fields should get a sample counterpart here. |
| `docs/js/components/*.js` | One render function per page/widget: `nav`, `header`, `overview` (hero/tiles/store grid/attention/compact OOS/store health), `stockouts`, `competition`, `forecast`, `alerts`, `metadata` (schema docs + product table w/ Latest|History toggle + search), `products` (the table), `storePanel` (slide-over per-store detail). |
| `docs/js/charts.js` | Hand-drawn SVG charts (trend, sparklines, horizontal/vertical bars, schematic store map). No chart lib. |
| `docs/js/util.js`, `icons.js` | `esc`, `badge`, `duration`, `clock`, `swatch`, `units` formatters; inline SVG icon set. |
| `docs/css/tokens.css`, `app.css` | Design tokens + layout/components (grid table classes like `.cols-products`, chips, badges, cards). |
| `docs/data/*.json` | Pre-baked payloads, one per tracked brand + `index.json` (default brand). Regenerated on every successful scrape-and-export; committed to git for GitHub Pages. |

### Other

| File | What it does |
|---|---|
| `app/dashboard.py`, `app/theme.py`, `app/map_render.py` | The **legacy Streamlit** UI — kept for reference, not the live product. Run with `streamlit run app/dashboard.py`. |
| `.github/workflows/update-data.yml` | Hourly workflow: install deps → `export_static_site.py` → commit DB + `docs/data`. Triggered by cron-job.org via the dispatches API (native GitHub cron proved unreliable; also, the scrape itself gets 403'd on runner IPs — see header comments). |
| `data/stock_tracker.db` | The SQLite history — **committed to git** so ephemeral workflow runs and fresh clones share it. |

---

## 4. Data contract (frontend ⇄ backend)

`webapp/server.py::build_dashboard()` returns this shape (mirrored by `SAMPLE`
in `docs/js/data.js`). The frontend does almost no computation — it formats.

- `meta` — platform, region, `updatedMinutesAgo`, `nextCheckMinutes`, `checkIntervalMinutes`
- `headline` — `availabilityPct`, `previousPct`, `rank`, `leaderName`, `productsInStock`, `hoursOffShelf`, **`peakHoursOffShelf`**, `averageOutageMinutes`
- `trend` — `days[]` + `series[][]` (per-brand daily availability %, IST-day buckets)
- `stockOnShelf` — units + share % per brand
- `tiles` — the 4 KPI tiles incl. **"Share gaps right now"** (your OOS SKUs at stores where a rival still has stock)
- `stores` — store × brand availability grid + map positions
- `stockouts` — per currently-OOS client SKU: `outBetween` ("15:37–15:46" window), `outRange` ("19h 18m–19h 28m"), `outDuringPeak`, `timesThisWeek`, `competitorInStock` (rival brand names), `nearby`, `productId`/`pincode` (for `/api/nearby`)
- `comparison`, `competitorStockouts` — brand table + rival outs (same honest ranges)
- `forecast` — `unitsLeft`, `sellingPerHour`, `hoursLeft` per depleting SKU
- `alerts` — notification feed (`time`, `type`, `text`)
- `products` — latest deduped row per product per store (the Metadata "Latest" view)
- `snapshotHistory` — **raw** snapshot rows, newest-first, capped at 2000 (the Metadata "Full history" view — the actual hourly "track")

---

## 5. Common tasks

```bash
# fresh env
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# run the live dashboard (localhost:8800)
cd webapp && uvicorn server:app --port 8800

# scrape once + regenerate static JSON (also what the scheduled job runs)
python scripts/export_static_site.py

# scrape + regenerate + commit + push to GitHub Pages
./refresh.command            # or double-click it in Finder

# inspect the data
sqlite3 data/stock_tracker.db "SELECT brand,name,inventory,is_sold_out,fetched_at FROM snapshots ORDER BY fetched_at DESC LIMIT 20;"
```

**Changing tracked brands/areas:** edit `config.py` (`TRACKED_BRANDS`,
`CLIENT_BRAND`, `SEARCH_QUERIES`, `GURGAON_LOCATIONS`). The whole pipeline
follows from there.

**Adding a dashboard field:** add it in `server.py::build_dashboard`, add a
sample value in `docs/js/data.js`, render it in the relevant
`docs/js/components/*.js`. Regenerate `docs/data/*.json` before pushing or the
static site won't see it.

**Known limitations (honest):** GitHub Actions can't scrape (403 on datacenter
IPs — refresh must come from a residential IP via `refresh.command` or a proxy);
check cadence bounds stock-out timing precision; depletion is a velocity
heuristic, not a demand model; no SKU↔SKU competitor mapping yet (share gaps
are brand-level); Zepto/Instamart scrapers are dormant reference code.
