"""FastAPI backend for the Shelf Pulse web frontend (webapp/frontend).

Serves GET /api/dashboard in exactly the shape of SAMPLE in
frontend/js/data.js, built from real Blinkit snapshots in the same SQLite
database the Streamlit app uses - no sample/placeholder values. Also serves
POST /api/nearby for the on-demand "check nearby stores" feature (deliberately
NOT run automatically for every stock-out on every page load, to respect
Blinkit's rate limits - see scrapers/blinkit.py).

Run with:
    cd webapp && uvicorn server:app --reload --port 8800
Then open http://localhost:8800
"""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("shelf_pulse.server")

# Everything is stored/computed internally in UTC (see storage/db.py) - this
# is purely a display-layer conversion for the India-based audience, applied
# right before formatting any *absolute* clock time (capturedAt, alert times,
# stock-out "since"). Relative figures (minutes-ago, hours-off-shelf, etc.)
# don't need this since a duration is the same length in any timezone.
IST = ZoneInfo("Asia/Kolkata")


def _ist(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert(IST)


def _fmt_dur(minutes: int) -> str:
    if minutes >= 60:
        h, m = divmod(minutes, 60)
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{minutes} min"


def _fmt_window(a, b) -> str:
    """'23:10–00:18' within a day, else '02 Nov 23:10 – 03 Nov 00:18'."""
    ta, tb = _ist(a), _ist(b)
    if ta.date() == tb.date():
        return f"{ta.strftime('%H:%M')}–{tb.strftime('%H:%M')}"
    return f"{ta.strftime('%d %b %H:%M')} – {tb.strftime('%d %b %H:%M')}"


def _in_peak(ts) -> bool:
    if ts is None or pd.isna(ts):
        return False
    return PEAK_START_HOUR_IST <= _ist(ts).hour < PEAK_END_HOUR_IST


def _out_bounds(first_out, last_in, now) -> tuple[int, str]:
    """(lower-bound minutes out, display range) for an open stock-out window:
    '45 min–1h 45m' when both bounds exist, '>45 min' when the product was
    already out at our first-ever observation (true duration unknowable)."""
    lo = max(0, int((now - pd.Timestamp(first_out)).total_seconds() / 60))
    if last_in is None or pd.isna(last_in):
        return lo, f">{_fmt_dur(lo)}"
    hi = max(lo, int((now - pd.Timestamp(last_in)).total_seconds() / 60))
    return lo, f"{_fmt_dur(lo)}–{_fmt_dur(hi)}"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analytics.metrics import (  # noqa: E402
    availability_by_brand,
    availability_by_store_brand,
    current_oos_alerts,
    current_stockout_window,
    depletion_forecast,
    latest_snapshot,
    oos_hours_by_daypart,
    oos_summary_stats,
    previous_snapshot,
    stock_on_shelf_by_brand,
    stockout_duration_hours,
    PEAK_START_HOUR_IST,
    PEAK_END_HOUR_IST,
)
from analytics.notifications import generate_notifications  # noqa: E402
from config import (  # noqa: E402
    AUTO_REFRESH_MINUTES,
    BRAND_COMPANIES,
    CATEGORY_LABEL,
    CLIENT_BRAND,
    DB_PATH,
    GURGAON_LOCATIONS,
    TRACKED_BRANDS,
)
from storage.db import init_db, load_notifications, load_snapshots, save_notifications  # noqa: E402

HERE = Path(__file__).parent
# Lives at docs/ (not webapp/frontend/) so the exact same static files are
# also what GitHub Pages serves - no separate copy to keep in sync. See
# scripts/export_static_site.py + .github/workflows/update-data.yml for the
# free-hosting path that doesn't use this FastAPI server at all.
FRONTEND_DIR = ROOT / "docs"
_DB_PATH = DB_PATH  # already an absolute path (anchored in config.py), safe regardless of process cwd
_TRACKED_LOCATION_NAMES = [loc["name"] for loc in GURGAON_LOCATIONS]

# Fixed CSS color vars (see frontend/css/tokens.css) - exactly 4 competitor
# slots are defined today. If TRACKED_BRANDS ever grows beyond 5, add more
# --c-* tokens to tokens.css and extend this list to match.
COMPETITOR_COLOR_VARS = ["--c-real", "--c-raw", "--c-bn", "--c-trop"]

# Schematic map positions (320x190 box) for known locations - same as the
# sample data's Sohna Road / Lajpat Nagar entries, so visual placement is
# consistent with the design. This is NOT a real map - just a layout
# position, same caveat as the Streamlit app's static map.
MAP_POSITIONS = {
    "Sohna Road": {"x": 118, "y": 162, "lx": 132, "ly": 166, "anchor": "start"},
    "Lajpat Nagar": {"x": 188, "y": 66, "lx": 188, "ly": 50, "anchor": "middle"},
}
_DEFAULT_MAP_POS = {"x": 160, "y": 95, "lx": 160, "ly": 115, "anchor": "middle"}

ALERT_TYPE_LABELS = {
    "stockout": "Out of stock",
    "restock": "Back in stock",
    "low_stock": "Running low",
    "new_sku": "New product",
    "delisting": "Delisted",
}


def _initials(name: str) -> str:
    parts = [p for p in name.replace("'", "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def _live_scoped(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df[df["location_name"].isin(_TRACKED_LOCATION_NAMES)]
    return df[~df["is_synthetic"]]


def _brand_list(df_brands: list[str], client_brand: str) -> list[dict]:
    others = [b for b in df_brands if b != client_brand]
    out = [{"name": client_brand, "colorVar": "--brand"}]
    for i, b in enumerate(others):
        out.append({"name": b, "colorVar": COMPETITOR_COLOR_VARS[i % len(COMPETITOR_COLOR_VARS)]})
    return out


def _avail_pct(df: pd.DataFrame, brand: str) -> float | None:
    sub = df[df["brand"] == brand]
    if sub.empty:
        return None
    return round(float((1 - sub["is_sold_out"].mean()) * 100))


def _day_buckets(df: pd.DataFrame, max_days: int = 7) -> list[pd.Timestamp]:
    # Bucketed by IST calendar date, not UTC - a 19:00 UTC reading is already
    # past midnight the next day in IST, so UTC-date bucketing would show it
    # under the wrong day for an India-based audience.
    days = sorted(df["fetched_at"].map(lambda t: _ist(t).date()).unique())
    days = days[-max_days:]
    if len(days) == 1:
        days = days * 2  # a single real day, shown twice so the line chart doesn't divide by zero
    return days


def _prior_check_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rows from before the most recent collector run - used to compute real
    "vs previous check" deltas without fabricating a weekly comparison we
    don't have enough history for yet."""
    if df.empty:
        return df
    latest_ts = df["fetched_at"].max()
    return df[df["fetched_at"] < latest_ts]


def _run_refresh() -> tuple[int, int]:
    """Live Blinkit collector run + Outbox notification diff. Shared by the
    background scheduler below and the manual POST /api/refresh route."""
    before_df = _live_scoped(load_snapshots(_DB_PATH))
    prev_latest = latest_snapshot(before_df) if not before_df.empty else before_df

    import collector as _collector
    n = _collector.run_once()

    after_df = _live_scoped(load_snapshots(_DB_PATH))
    new_latest = latest_snapshot(after_df) if not after_df.empty else after_df
    notifs = generate_notifications(prev_latest, new_latest, TRACKED_BRANDS, CLIENT_BRAND)
    if notifs:
        save_notifications(_DB_PATH, notifs)
    return n, len(notifs)


async def _scheduler_loop() -> None:
    """Collects on a fixed, steady cadence (every AUTO_REFRESH_MINUTES) in the
    background, independent of page traffic - not "refresh whenever someone
    happens to load the page", which produced wildly uneven gaps between
    snapshots (13 minutes one time, 90 the next). The depletion-forecast
    velocity math only means something if the points it's built from are
    evenly spaced; this is what actually fixes that, not a formula tweak.
    Runs once immediately on startup, then every AUTO_REFRESH_MINUTES forever.
    """
    loop = asyncio.get_event_loop()
    while True:
        try:
            n, n_notifs = await loop.run_in_executor(None, _run_refresh)
            logger.info("Scheduled refresh: %d rows, %d new alerts", n, n_notifs)
        except Exception:
            logger.exception("Scheduled refresh failed - will retry next cycle")
        await asyncio.sleep(AUTO_REFRESH_MINUTES * 60)


_scheduler_task: asyncio.Task | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _scheduler_task
    init_db(_DB_PATH)
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    yield
    if _scheduler_task:
        _scheduler_task.cancel()


def build_dashboard(brand: str | None = None) -> dict:
    # No refresh-on-request here anymore - the background scheduler (see
    # _scheduler_loop) keeps data fresh on a steady cadence independent of
    # page traffic. This just reads whatever's currently in SQLite, so page
    # loads are fast and never block on a live scrape.
    df_all = load_snapshots(_DB_PATH)
    df = _live_scoped(df_all)

    tracked = [b for b in TRACKED_BRANDS if not df.empty and b in set(df["brand"].unique())] or TRACKED_BRANDS
    client_brand = brand if brand in tracked else (CLIENT_BRAND if CLIENT_BRAND in tracked else (tracked[0] if tracked else CLIENT_BRAND))
    df = df[df["brand"].isin(tracked)] if not df.empty else df

    if df.empty:
        # No data at all yet - return a minimal, honestly-empty shaped payload
        # rather than fabricating numbers. The frontend will show zeros.
        brands = _brand_list(tracked, client_brand)
        return _empty_payload(client_brand, brands)

    latest = latest_snapshot(df)
    prev = previous_snapshot(df)
    prior_df = _prior_check_df(df)

    brands = _brand_list(tracked, client_brand)
    brand_names = [b["name"] for b in brands]

    avail = availability_by_brand(df)
    stats = oos_summary_stats(df, client_brand)

    data_age_minutes = (pd.Timestamp.now(tz="UTC") - df["fetched_at"].max()).total_seconds() / 60

    # ---- headline ----
    client_pct = _avail_pct(latest, client_brand) or 0
    prev_client_pct = _avail_pct(prev, client_brand) if not prev.empty else None
    brand_pcts = {b: (_avail_pct(latest, b) or 0) for b in brand_names}
    ranking = sorted(brand_names, key=lambda b: brand_pcts[b], reverse=True)
    rank = ranking.index(client_brand) + 1
    leader_name = ranking[0]
    points_behind_leader = max(0, brand_pcts[leader_name] - client_pct) if leader_name != client_brand else 0

    prior_hours_off_shelf = 0.0
    if not prior_df.empty:
        prior_dur = stockout_duration_hours(prior_df[prior_df["brand"] == client_brand], only_affected=False)
        prior_hours_off_shelf = float(prior_dur["oos_hours"].sum()) if not prior_dur.empty else 0.0

    # Peak (6-11 PM IST) vs off-peak split - a stock-out during peak selling
    # hours costs far more than an overnight one.
    daypart = oos_hours_by_daypart(df[df["brand"] == client_brand])
    peak_hours_off_shelf = float(daypart.iloc[0]["oos_hours_peak"]) if not daypart.empty else 0.0

    headline = {
        "availabilityPct": client_pct,
        "previousPct": round(prev_client_pct) if prev_client_pct is not None else client_pct,
        "rank": rank,
        "productsInStock": stats["skus_in_stock"],
        "leaderName": leader_name,
        "pointsBehindLeader": round(points_behind_leader),
        "hoursOffShelf": round(stats["hours_off_shelf"]),
        "peakHoursOffShelf": round(peak_hours_off_shelf, 1),
        "hoursOffShelfChange": round(stats["hours_off_shelf"] - prior_hours_off_shelf, 1),
        "averageOutageMinutes": round(stats["avg_outage_hours"] * 60) if stats["avg_outage_hours"] is not None else 0,
    }

    # ---- 7-day trend (real daily buckets - may be fewer than 7 if the
    # collector hasn't been running that long; not padded with fake days) ----
    days = _day_buckets(df)
    day_labels = [d.strftime("%-d %b") if hasattr(d, "strftime") else str(d) for d in days]
    dfd = df.copy()
    dfd["_date"] = dfd["fetched_at"].map(lambda t: _ist(t).date())
    series = []
    for b in brand_names:
        row = []
        for d in days:
            day_rows = dfd[(dfd["_date"] == d) & (dfd["brand"] == b)]
            row.append(_avail_pct(day_rows, b) if not day_rows.empty else brand_pcts.get(b, 0))
        series.append(row)

    # ---- stock on shelf ----
    shelf = stock_on_shelf_by_brand(df)
    prior_shelf = stock_on_shelf_by_brand(prior_df) if not prior_df.empty else pd.DataFrame(columns=["brand", "units"])
    prior_units = dict(zip(prior_shelf.get("brand", []), prior_shelf.get("units", [])))
    stock_on_shelf = []
    for _, row in shelf.iterrows():
        if row["brand"] not in brand_names:
            continue
        idx = brand_names.index(row["brand"])
        prior_u = prior_units.get(row["brand"])
        change_pct = round((row["units"] - prior_u) / prior_u * 100) if prior_u else 0
        stock_on_shelf.append({"brand": idx, "units": int(row["units"]), "changePct": change_pct})

    # ---- tiles ----
    client_oos_now = stats["oos_now"]
    prev_client_oos = int(prev[prev["brand"] == client_brand]["is_sold_out"].sum()) if not prev.empty else client_oos_now
    oos_delta_n = client_oos_now - prev_client_oos

    forecast_df = depletion_forecast(df[df["brand"] == client_brand])
    running_out_soon = forecast_df[forecast_df["est_hours_to_stockout"] <= 6] if not forecast_df.empty else forecast_df
    running_out_names = ", ".join(running_out_soon["name"].head(2).tolist()) if not running_out_soon.empty else "None right now"

    competitors_oos_now = stats["competitors_oos_now"]
    non_client_prev = prev[prev["brand"] != client_brand] if not prev.empty else prev
    prev_competitors_oos = int(non_client_prev["is_sold_out"].sum()) if not non_client_prev.empty else competitors_oos_now
    competitor_delta_n = competitors_oos_now - prev_competitors_oos

    client_oos_latest = current_oos_alerts(df)
    client_oos_latest = client_oos_latest[client_oos_latest["brand"] == client_brand] if not client_oos_latest.empty else client_oos_latest

    # Which competitor brands still have stock at each store right now -
    # powers the "share gap" opportunity metric: your SKU is out while a
    # rival can still capture the sale at the same dark store.
    comp_in_stock_by_store = {
        loc: sorted(latest[(latest["location_name"] == loc) & (latest["brand"] != client_brand) & (~latest["is_sold_out"])]["brand"].unique())
        for loc in _TRACKED_LOCATION_NAMES
    }
    gap_count = int(sum(1 for _, r in client_oos_latest.iterrows() if comp_in_stock_by_store.get(r["location_name"])))

    def _flat_trend(value: float, n: int) -> list[float]:
        # We don't have reliable historical reconstruction for every tile yet
        # (e.g. forecast / nearby-stock counts aren't stored per day) - a flat
        # line at the real current value is honest; it's not claiming a false
        # trend, just showing "no change detected in available history".
        return [value] * max(2, n)

    oos_trend = []
    for d in days:
        day_rows = dfd[(dfd["_date"] == d) & (dfd["brand"] == client_brand)]
        oos_trend.append(int(day_rows.groupby("product_id")["is_sold_out"].last().sum()) if not day_rows.empty else client_oos_now)

    competitor_oos_trend = []
    for d in days:
        day_rows = dfd[(dfd["_date"] == d) & (dfd["brand"] != client_brand)]
        competitor_oos_trend.append(int(day_rows.groupby(["brand", "product_id"])["is_sold_out"].last().sum()) if not day_rows.empty else competitors_oos_now)

    tiles = [
        {
            "label": "Out of stock right now", "value": client_oos_now, "unit": f"of {stats['skus_tracked']}",
            "delta": (f"{abs(oos_delta_n)} more" if oos_delta_n > 0 else (f"{abs(oos_delta_n)} fewer" if oos_delta_n < 0 else "")),
            "deltaTone": "bad" if oos_delta_n > 0 else "good", "note": "than the last check", "tone": "crit",
            "trend": oos_trend,
        },
        {
            "label": "Running out in 6 hours", "value": int(len(running_out_soon)), "unit": "products",
            "delta": "", "deltaTone": "bad", "note": running_out_names, "tone": "warn",
            "trend": _flat_trend(len(running_out_soon), len(days)),
        },
        {
            "label": "Share gaps right now", "value": gap_count, "unit": f"of {client_oos_now} products out",
            "delta": "", "deltaTone": "bad", "note": "of your out-of-stock products sit at a store where a rival still has stock - the sale goes to them", "tone": "crit",
            "trend": _flat_trend(gap_count, len(days)),
        },
        {
            "label": "Competitors out of stock", "value": competitors_oos_now, "unit": "products",
            "delta": (f"{abs(competitor_delta_n)} more" if competitor_delta_n > 0 else (f"{abs(competitor_delta_n)} fewer" if competitor_delta_n < 0 else "")),
            "deltaTone": "good" if competitor_delta_n > 0 else "bad", "note": "chances to win the shelf", "tone": "brand",
            "trend": competitor_oos_trend,
        },
    ]

    # ---- stores (store x brand availability grid + schematic map) ----
    store_brand = availability_by_store_brand(df)
    stores = []
    for loc in _TRACKED_LOCATION_NAMES:
        values = []
        for b in brand_names:
            row = store_brand[(store_brand["location_name"] == loc) & (store_brand["brand"] == b)]
            values.append(round(float(row.iloc[0]["availability_pct"])) if not row.empty else 0)
        city = next((l["city"] for l in GURGAON_LOCATIONS if l["name"] == loc), "")
        stores.append({"name": loc, "city": city, "values": values, "map": MAP_POSITIONS.get(loc, _DEFAULT_MAP_POS)})

    # ---- stock-outs (client brand) ----
    # Interval-censored windows, not point estimates: a product observed in
    # stock at 12:00 and out at 1:00 went out *sometime in that hour* - the
    # honest bound is (last in-stock check, first out-of-stock check), and it
    # tightens as check frequency increases. FMCG-correct framing.
    window_df = current_stockout_window(df[df["brand"] == client_brand])
    dur_df = stockout_duration_hours(df[df["brand"] == client_brand])
    now = pd.Timestamp.now(tz="UTC")
    stockouts = []
    if not client_oos_latest.empty:
        for _, row in client_oos_latest.iterrows():
            w = window_df[(window_df["location_name"] == row["location_name"]) & (window_df["product_id"] == row["product_id"])]
            first_out = w.iloc[0]["first_out_at"] if not w.empty else row["fetched_at"]
            last_in = w.iloc[0]["last_in_stock_at"] if not w.empty else None
            has_last_in = last_in is not None and pd.notna(last_in)
            minutes_out, out_range = _out_bounds(first_out, last_in, now)
            out_between = _fmt_window(last_in, first_out) if has_last_in else f"before {_ist(first_out).strftime('%d %b %H:%M')}"
            dur_row = dur_df[(dur_df["location_name"] == row["location_name"]) & (dur_df["name"] == row["name"])]
            times_this_week = int(dur_row.iloc[0]["oos_episodes"]) if not dur_row.empty else 1
            rivals = comp_in_stock_by_store.get(row["location_name"], [])
            stockouts.append({
                "product": row["name"], "pack": row["unit"] or "", "mrp": round(float(row["mrp"] or row["price"] or 0)),
                "store": row["location_name"], "since": _ist(first_out).strftime("%H:%M"),
                "outBetween": out_between, "outRange": out_range,
                "outDuringPeak": _in_peak(first_out) or _in_peak(last_in),
                "minutesOut": minutes_out, "timesThisWeek": times_this_week,
                # Real-time multi-store checks are rate-limited and only run
                # on demand (POST /api/nearby), not automatically for every
                # row on every page load - see README "Wiring real data".
                "nearby": {"tone": "neutral", "text": "Check nearby stores"},
                # Real data now: rival brands with any in-stock product at the
                # same store (share gap), not a SKU-level product mapping.
                "competitorInStock": ", ".join(rivals) if rivals else None,
                # Extra fields beyond the original contract - the frontend's
                # "Check nearby stores" button needs these to call /api/nearby.
                "productId": row["product_id"], "pincode": row.get("pincode", ""),
            })

    hours_off_shelf = [
        {"product": f"{r['name']} {r['unit']}".strip(), "hours": round(float(r["oos_hours"]), 1)}
        for _, r in dur_df.sort_values("oos_hours", ascending=False).head(6).iterrows()
    ] if not dur_df.empty else []

    stockouts_by_store = [
        {"store": loc, "count": int(len(client_oos_latest[client_oos_latest["location_name"] == loc])) if not client_oos_latest.empty else 0}
        for loc in _TRACKED_LOCATION_NAMES
    ]

    # ---- competition ----
    oos_now_latest = current_oos_alerts(df)
    comparison = []
    for i, b in enumerate(brand_names):
        pct = brand_pcts.get(b, 0)
        prev_pct = _avail_pct(prev, b) if not prev.empty else pct
        products = int(latest[latest["brand"] == b]["product_id"].nunique())
        out_now = int(oos_now_latest[oos_now_latest["brand"] == b]["product_id"].nunique()) if not oos_now_latest.empty else 0
        comparison.append({"brand": i, "availabilityPct": pct, "previousPct": round(prev_pct) if prev_pct is not None else pct, "products": products, "outNow": out_now})

    competitor_oos = oos_now_latest[oos_now_latest["brand"] != client_brand] if not oos_now_latest.empty else oos_now_latest
    competitor_window = current_stockout_window(df[df["brand"] != client_brand])
    competitor_stockouts = []
    if not competitor_oos.empty:
        for _, row in competitor_oos.head(10).iterrows():
            w = competitor_window[(competitor_window["location_name"] == row["location_name"]) & (competitor_window["product_id"] == row["product_id"])]
            first_out = w.iloc[0]["first_out_at"] if not w.empty else row["fetched_at"]
            last_in = w.iloc[0]["last_in_stock_at"] if not w.empty else None
            minutes_out, out_range = _out_bounds(first_out, last_in, now)
            # product names usually already include the brand - don't double it
            disp = row["name"] if str(row["name"]).lower().startswith(str(row["brand"]).lower()) else f"{row['brand']} {row['name']}"
            competitor_stockouts.append({
                "product": disp, "pack": row["unit"] or "", "store": row["location_name"],
                "minutesOut": minutes_out, "outRange": out_range,
                "yourOption": None,  # no product<->competitor mapping exists yet
            })

    # ---- forecast ---- (depletion_forecast() doesn't carry `unit`, so look it up from `latest`)
    forecast = []
    if not forecast_df.empty:
        unit_lookup = latest.set_index(["product_id", "location_name"])["unit"].to_dict()
        for _, r in forecast_df.head(10).iterrows():
            forecast.append({
                "product": r["name"], "pack": unit_lookup.get((r["product_id"], r["location_name"]), "") or "", "store": r["location_name"],
                "unitsLeft": int(r["current_inventory"]), "sellingPerHour": round(float(r["depletion_rate_per_hr"]), 1),
                "hoursLeft": round(float(r["est_hours_to_stockout"]), 1),
            })

    # ---- full product catalog (every tracked brand, every product, latest
    # inventory per store) - the individual-product/inventory view that
    # existed in the Streamlit app's OOS/KPI drill-down tables, but has no
    # equivalent page in the new design yet. Not part of the original API
    # contract - added because it was a real feature being lost in the port.
    # Field names mirror the actual `snapshots` SQLite columns closely (not
    # just a curated subset) so the Metadata page is a faithful view of what's
    # really stored, not an approximation - see storage/db.py's SCHEMA. ----
    products = []
    for _, r in latest.sort_values(["brand", "location_name", "name"]).iterrows():
        products.append({
            "brand": r["brand"], "product": r["name"], "pack": r["unit"] or "", "store": r["location_name"],
            "merchantId": r["merchant_id"] or "", "price": round(float(r["price"] or 0)),
            "mrp": round(float(r["mrp"] or 0)), "inventory": int(r["inventory"] or 0),
            "status": "Out of stock" if r["is_sold_out"] else "In stock",
            # Sent pre-formatted (unlike most other timestamps in this payload,
            # which send raw minutes/HH:MM for the frontend to format) because
            # rows here can span the full 30-day retention window, not just
            # "today" - there's no existing frontend helper for formatting an
            # arbitrary past date, only same-day "HH:MM" (see util.js clock()).
            "capturedAt": _ist(r["fetched_at"]).strftime("%d %b, %H:%M") + " IST",
        })

    # ---- raw snapshot history: one row per scrape run (NOT deduplicated to
    # latest like `products` above) - this is the actual append-only "track"
    # the `snapshots` table accumulates every hour, so a user can watch the
    # same product's inventory/status change run-over-run. Capped at 2000
    # rows (newest first) so the static GitHub Pages JSON stays a sane size
    # at ~330-390 rows per hourly scrape; locally the full 30-day history is
    # still in SQLite regardless. ----
    snapshot_history = []
    hist = df.sort_values("fetched_at", ascending=False).head(2000)
    for _, r in hist.iterrows():
        snapshot_history.append({
            "brand": r["brand"], "product": r["name"], "pack": r["unit"] or "", "store": r["location_name"],
            "merchantId": r["merchant_id"] or "", "productId": r["product_id"] or "", "price": round(float(r["price"] or 0)),
            "mrp": round(float(r["mrp"] or 0)), "inventory": int(r["inventory"] or 0),
            "status": "Out of stock" if r["is_sold_out"] else "In stock",
            "capturedAt": _ist(r["fetched_at"]).strftime("%d %b, %H:%M") + " IST",
        })

    # ---- alerts ----
    notif_df = load_notifications(_DB_PATH)
    alerts = []
    if not notif_df.empty:
        for _, r in notif_df.head(100).iterrows():
            alerts.append({
                "time": _ist(r["created_at"]).strftime("%H:%M"),
                "type": ALERT_TYPE_LABELS.get(r["type"], r["type"]),
                "text": r["message"],
            })

    return {
        "meta": {
            "platform": "Blinkit",  # only Blinkit has real data wired up - see README
            "region": "Delhi NCR", "category": CATEGORY_LABEL, "period": "7D",
            "updatedMinutesAgo": round(data_age_minutes), "storesChecked": len(_TRACKED_LOCATION_NAMES),
            "checkIntervalMinutes": AUTO_REFRESH_MINUTES,
            "nextCheckMinutes": max(0, round(AUTO_REFRESH_MINUTES - data_age_minutes)),
        },
        "brand": {
            "name": client_brand, "company": BRAND_COMPANIES.get(client_brand, ""),
            "initials": _initials(client_brand), "totalProducts": stats["skus_tracked"],
        },
        "brands": brands,
        "headline": headline,
        "trend": {"days": day_labels, "series": series},
        "stockOnShelf": stock_on_shelf,
        "tiles": tiles,
        "stores": stores,
        "stockouts": stockouts,
        "attention": _build_attention(stockouts, forecast, competitor_stockouts, client_brand),
        "hoursOffShelf": hours_off_shelf,
        "stockoutsByStore": stockouts_by_store,
        "comparison": comparison,
        "competitorStockouts": competitor_stockouts,
        "forecast": forecast,
        "alerts": alerts,
        "products": products,
        "snapshotHistory": snapshot_history,
    }


def _build_attention(stockouts, forecast, competitor_stockouts, client_brand: str) -> list[dict]:
    """Real "needs your attention" items, built from the same data already
    computed above - not a separate fabricated list."""
    items = []
    if stockouts:
        worst = max(stockouts, key=lambda s: s["minutesOut"])
        items.append({
            "tone": "crit", "title": f"{worst['product']} {worst['pack']} is out at {worst['store']}",
            "detail": "Open Stock-outs to check nearby stores for stock", "action": "Check", "goTo": "stock",
        })
    urgent_forecast = [f for f in forecast if f["hoursLeft"] <= 6]
    if urgent_forecast:
        f = urgent_forecast[0]
        items.append({
            "tone": "warn", "title": f"{f['product']} will run out in about {f['hoursLeft']:g} hours",
            "detail": f"{f['unitsLeft']} left at {f['store']}, selling about {f['sellingPerHour']:g} an hour",
            "action": "Reorder", "goTo": "forecast",
        })
    if competitor_stockouts:
        c = competitor_stockouts[0]
        items.append({
            "tone": "brand", "title": f"{c['product']} is out of stock at {c['store']}",
            "detail": "A competitor gap you may be able to win", "action": "Compare", "goTo": "competition",
        })
    if len(stockouts) > 1:
        items.append({
            "tone": "crit", "title": f"{len(stockouts)} {client_brand} products are currently out of stock",
            "detail": "See the full list on Stock-outs", "action": "View", "goTo": "stock",
        })
    return items[:4]


def _empty_payload(client_brand: str, brands: list[dict]) -> dict:
    return {
        "meta": {"platform": "Blinkit", "region": "Delhi NCR", "category": CATEGORY_LABEL, "period": "7D",
                 "updatedMinutesAgo": 0, "storesChecked": len(_TRACKED_LOCATION_NAMES),
                 "checkIntervalMinutes": AUTO_REFRESH_MINUTES, "nextCheckMinutes": AUTO_REFRESH_MINUTES},
        "brand": {"name": client_brand, "company": BRAND_COMPANIES.get(client_brand, ""), "initials": _initials(client_brand), "totalProducts": 0},
        "brands": brands,
        "headline": {"availabilityPct": 0, "previousPct": 0, "rank": 1, "productsInStock": 0, "leaderName": client_brand,
                     "pointsBehindLeader": 0, "hoursOffShelf": 0, "hoursOffShelfChange": 0, "averageOutageMinutes": 0},
        "trend": {"days": ["—", "—"], "series": [[0, 0] for _ in brands]},
        "stockOnShelf": [], "tiles": [
            {"label": "Out of stock right now", "value": 0, "unit": "of 0", "delta": "", "deltaTone": "good", "note": "No data yet", "tone": "crit", "trend": [0, 0]},
            {"label": "Running out in 6 hours", "value": 0, "unit": "products", "delta": "", "deltaTone": "good", "note": "No data yet", "tone": "warn", "trend": [0, 0]},
            {"label": "Stock at nearby stores", "value": 0, "unit": "of 0", "delta": "", "deltaTone": "good", "note": "No data yet", "tone": "ok", "trend": [0, 0]},
            {"label": "Competitors out of stock", "value": 0, "unit": "products", "delta": "", "deltaTone": "good", "note": "No data yet", "tone": "brand", "trend": [0, 0]},
        ],
        "stores": [{"name": loc["name"], "city": loc["city"], "values": [0] * len(brands), "map": MAP_POSITIONS.get(loc["name"], _DEFAULT_MAP_POS)} for loc in GURGAON_LOCATIONS],
        "stockouts": [], "attention": [], "hoursOffShelf": [], "stockoutsByStore": [], "comparison": [], "competitorStockouts": [], "forecast": [], "alerts": [], "products": [],
    }


app = FastAPI(title="Shelf Pulse", lifespan=_lifespan)


@app.get("/api/dashboard")
def dashboard(platform: str = Query("Blinkit"), period: str = Query("7D"), brand: str | None = Query(None)):
    return build_dashboard(brand=brand)


class NearbyRequest(BaseModel):
    product_id: str
    location_name: str
    pincode: str = ""


@app.post("/api/nearby")
def check_nearby(req: NearbyRequest):
    """On-demand nearby-store check for one product at one location - the same
    live Blinkit lookup used by the Streamlit app's "Check nearby stores"
    button. Deliberately not run automatically for every row (see module
    docstring)."""
    from scrapers.blinkit import BlinkitScraper, RateLimitedError

    loc = next((l for l in GURGAON_LOCATIONS if l["name"] == req.location_name), None)
    if loc is None:
        return {"results": []}

    scraper = BlinkitScraper()
    results = []
    try:
        merchants = scraper.get_merchants(loc["lat"], loc["lon"])
    except Exception:
        return {"results": []}

    for m in merchants[1:4]:
        time.sleep(1.0)
        try:
            alt = scraper.get_product_at_merchant(req.product_id, m["id"], loc["lat"], loc["lon"], req.location_name, req.pincode)
        except RateLimitedError:
            results.append({"store": m["id"], "tone": "neutral", "text": "Check failed (rate limited)"})
            continue
        if alt is None:
            results.append({"store": m["id"], "tone": "neutral", "text": "Not sold at this store"})
        elif alt.is_sold_out:
            results.append({"store": m["id"], "tone": "crit", "text": "Out nearby too"})
        else:
            results.append({"store": m["id"], "tone": "ok", "text": f"{alt.inventory} at store {m['id']}"})
    return {"results": results}


@app.post("/api/refresh")
def refresh():
    """Manual refresh - triggers a live Blinkit collector run, same as the
    Streamlit app's "Refresh now" button, and generates Outbox alerts from
    the before/after diff. (Also marks the debounce clock so the automatic
    stale-data check doesn't immediately re-trigger right after this.)"""
    global _last_auto_refresh_attempt
    n, n_notifs = _run_refresh()
    _last_auto_refresh_attempt = time.time()
    return {"rows_collected": n, "new_alerts": n_notifs}


# Serve index.html, css/ and js/ from the frontend folder (mounted last so /api wins)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
