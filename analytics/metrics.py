"""Core analytics: OOS detection, competitive benchmarking, depletion prediction."""
from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

# Peak selling window for Indian quick-commerce, in IST. Stock-outs inside
# this window cost far more than overnight ones - a core FMCG distinction the
# dashboard reports separately (see oos_hours_by_daypart).
IST = ZoneInfo("Asia/Kolkata")
PEAK_START_HOUR_IST = 18  # 6 PM
PEAK_END_HOUR_IST = 23    # through 10:59 PM


def _ist_hour(ts) -> int:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert(IST).hour


def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent row per (platform, location, product_id)."""
    if df.empty:
        return df
    idx = df.groupby(["platform", "location_name", "product_id"])["fetched_at"].idxmax()
    return df.loc[idx].reset_index(drop=True)


def previous_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Second-most-recent row per (platform, location, product_id), where it exists.

    Used to compute real "vs previous check" deltas on KPI cards - only meaningful
    once `collector.py` has been run more than once, so callers should treat an
    empty result as "no prior comparison available yet" rather than assuming 0.
    """
    if df.empty:
        return df
    ranked = df.sort_values("fetched_at", ascending=False)
    ranked["_rank"] = ranked.groupby(["platform", "location_name", "product_id"]).cumcount()
    return ranked[ranked["_rank"] == 1].drop(columns="_rank").reset_index(drop=True)


def availability_by(df: pd.DataFrame, dimension: str = "brand") -> pd.DataFrame:
    """% of observed rows where each `dimension` value (brand / location_name / ...)
    was in stock, split by platform. Powers the "View by" toggle on the
    competitive-benchmarking chart.
    """
    cols = [dimension, "platform", "availability_pct", "observations"]
    if df.empty or dimension not in df.columns:
        return pd.DataFrame(columns=cols)
    g = (
        df.groupby([dimension, "platform"])
        .agg(observations=("is_sold_out", "size"), stockouts=("is_sold_out", "sum"))
        .reset_index()
    )
    g["availability_pct"] = (1 - g["stockouts"] / g["observations"]) * 100
    return g.sort_values(["platform", "availability_pct"], ascending=[True, False])


def availability_by_brand(df: pd.DataFrame) -> pd.DataFrame:
    """% of observed (platform, location, time-bucket) rows where each brand was in stock.

    This is the core competitive-benchmarking metric: who's actually on shelf
    (virtually) most often across Gurgaon dark stores.
    """
    return availability_by(df, "brand")


def location_summary(df: pd.DataFrame, client_brand: str | None = None) -> pd.DataFrame:
    """Per-location rollup for the map view: SKU count, OOS count/%, and the
    client brand's OOS count, from the latest snapshot at each location.
    """
    latest = latest_snapshot(df)
    if latest.empty:
        return pd.DataFrame(
            columns=["location_name", "pincode", "skus_tracked", "oos_count", "oos_pct", "client_oos_count"]
        )

    def _agg(grp: pd.DataFrame) -> pd.Series:
        client_oos = (
            int(grp[(grp["brand"] == client_brand)]["is_sold_out"].sum()) if client_brand else 0
        )
        return pd.Series(
            {
                "pincode": grp["pincode"].iloc[0],
                "skus_tracked": len(grp),
                "oos_count": int(grp["is_sold_out"].sum()),
                "oos_pct": round(grp["is_sold_out"].mean() * 100, 1),
                "client_oos_count": client_oos,
            }
        )

    return latest.groupby("location_name").apply(_agg, include_groups=False).reset_index()


def current_oos_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """Products that are sold out right now, per the latest snapshot."""
    latest = latest_snapshot(df)
    if latest.empty:
        return latest
    return latest[latest["is_sold_out"]].sort_values(["platform", "location_name", "brand"])


def stockout_duration_hours(df: pd.DataFrame, only_affected: bool = True) -> pd.DataFrame:
    """For each (platform, location, product), estimate total hours observed as
    sold-out and the number of distinct stock-out episodes, from the snapshot history.

    `only_affected=True` (default) drops SKUs with zero recorded stock-outs, since
    showing `0 / 0` rows under a "stock-out" heading reads as an alarm when it's
    actually the good outcome - easy to misread as "this item is out of stock".
    """
    if df.empty:
        return pd.DataFrame(columns=["platform", "location_name", "brand", "name", "unit", "oos_hours", "oos_episodes"])

    rows = []
    key_cols = ["platform", "location_name", "product_id", "brand", "name", "unit"]
    for keys, grp in df.sort_values("fetched_at").groupby(key_cols):
        grp = grp.reset_index(drop=True)
        oos_hours = 0.0
        episodes = 0
        prev_time = None
        prev_sold_out = False
        for _, row in grp.iterrows():
            if prev_time is not None:
                gap_hours = (row["fetched_at"] - prev_time).total_seconds() / 3600
                if prev_sold_out:
                    oos_hours += gap_hours
            if row["is_sold_out"] and not prev_sold_out:
                episodes += 1
            prev_time = row["fetched_at"]
            prev_sold_out = row["is_sold_out"]
        rows.append(dict(zip(key_cols, keys), oos_hours=round(oos_hours, 1), oos_episodes=episodes))
    result = pd.DataFrame(rows).sort_values("oos_hours", ascending=False)
    if only_affected:
        result = result[result["oos_episodes"] > 0]
    return result


def availability_by_store_brand(df: pd.DataFrame) -> pd.DataFrame:
    """Availability % per (location_name, brand) - the "store x brand" grid.

    `location_name` is used as the store axis (not `merchant_id`) because the
    primary-store search is what actually discovers each tracked brand's full
    catalog at a given point, and that's what's polled repeatedly - matching
    the existing single-store-per-location assumption used elsewhere in the
    dashboard (map, KPIs). Real multi-merchant-per-location data exists only
    for ad-hoc "check nearby stores" lookups, not as a repeated time series.
    """
    cols = ["location_name", "brand", "availability_pct", "observations"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = (
        df.groupby(["location_name", "brand"])
        .agg(observations=("is_sold_out", "size"), stockouts=("is_sold_out", "sum"))
        .reset_index()
    )
    g["availability_pct"] = (1 - g["stockouts"] / g["observations"]) * 100
    return g[cols]


def stock_on_shelf_by_brand(df: pd.DataFrame) -> pd.DataFrame:
    """Total units currently on shelf per brand (sum of latest inventory across
    all tracked locations), plus each brand's share of total tracked units.
    Real inventory counts, as reported by the platform - not an estimate.
    """
    cols = ["brand", "units", "share_pct"]
    latest = latest_snapshot(df)
    if latest.empty:
        return pd.DataFrame(columns=cols)
    g = latest.groupby("brand")["inventory"].sum().reset_index(name="units")
    total = g["units"].sum()
    g["share_pct"] = (g["units"] / total * 100) if total else 0
    return g.sort_values("units", ascending=False)[cols]


def oos_summary_stats(df: pd.DataFrame, client_brand: str) -> dict:
    """Headline/tile numbers for the Overview page, all derived from real
    snapshot history - no fabricated figures. Returns a plain dict since these
    are single scalars, not a table.
    """
    latest = latest_snapshot(df)
    client_latest = latest[latest["brand"] == client_brand]
    client_oos_now = client_latest[client_latest["is_sold_out"]]

    dur = stockout_duration_hours(df[df["brand"] == client_brand], only_affected=False)
    hours_off_shelf = dur["oos_hours"].sum() if not dur.empty else 0.0

    # Average total OOS hours so far, among the brand's SKUs that have actually
    # had at least one stock-out episode - not a global average across all SKUs.
    avg_outage_hours = dur[dur["oos_hours"] > 0]["oos_hours"].mean() if not dur.empty else None

    non_client = latest[latest["brand"] != client_brand]
    competitors_oos_now = int(non_client["is_sold_out"].sum()) if not non_client.empty else 0

    return {
        "skus_tracked": int(client_latest["product_id"].nunique()),
        "skus_in_stock": int(client_latest["product_id"].nunique()) - int(client_oos_now["product_id"].nunique()),
        "oos_now": int(client_oos_now["product_id"].nunique()),
        "hours_off_shelf": round(float(hours_off_shelf), 1),
        "avg_outage_hours": round(float(avg_outage_hours), 1) if avg_outage_hours is not None and pd.notna(avg_outage_hours) else None,
        "competitors_oos_now": competitors_oos_now,
    }


def needs_attention(df: pd.DataFrame, client_brand: str, max_items: int = 4) -> pd.DataFrame:
    """Real, actionable rows for the "Needs your attention" list: the client
    brand's currently sold-out SKUs, worst-outage-first. (Nearby-store stock
    and competitor-gap context are added live elsewhere - the "check nearby
    stores" feature - since those require on-demand API calls, not something
    safe to run automatically on every page load.)
    """
    cols = ["brand", "name", "location_name", "oos_hours", "oos_episodes"]
    oos = current_oos_alerts(df[df["brand"] == client_brand])
    if oos.empty:
        return pd.DataFrame(columns=cols)
    dur = stockout_duration_hours(df[df["brand"] == client_brand])
    merged = oos.merge(dur, on=["platform", "location_name", "product_id", "brand", "name"], how="left")
    merged["oos_hours"] = merged["oos_hours"].fillna(0.0)
    merged["oos_episodes"] = merged["oos_episodes"].fillna(1).astype(int)
    return merged.sort_values("oos_hours", ascending=False).head(max_items)[cols]


def current_stockout_started_at(df: pd.DataFrame) -> pd.DataFrame:
    """For each (platform, location, product) that is sold out right now, find
    when the *current* sold-out streak actually began - i.e. the earliest
    consecutive "is_sold_out" reading ending at the latest snapshot. Used for
    an honest "since HH:MM" / "out for N minutes" figure instead of reusing the
    latest check's timestamp (which would understate how long it's been out).
    """
    cols = ["platform", "location_name", "product_id", "brand", "name", "since"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    rows = []
    key_cols = ["platform", "location_name", "product_id", "brand", "name"]
    for keys, grp in df.sort_values("fetched_at").groupby(key_cols):
        grp = grp.reset_index(drop=True)
        if not bool(grp.iloc[-1]["is_sold_out"]):
            continue  # not currently sold out
        since = grp.iloc[-1]["fetched_at"]
        for i in range(len(grp) - 1, -1, -1):
            if bool(grp.iloc[i]["is_sold_out"]):
                since = grp.iloc[i]["fetched_at"]
            else:
                break
        rows.append(dict(zip(key_cols, keys), since=since))
    return pd.DataFrame(rows, columns=cols)


def current_stockout_window(df: pd.DataFrame) -> pd.DataFrame:
    """The honest censoring window for each product sold out right now: it went
    out sometime between `last_in_stock_at` (the last check that still saw it in
    stock, if we ever saw it in stock) and `first_out_at` (the first check of the
    current sold-out streak). FMCG-correct framing - a between-checks stock-out
    is a bounded interval, not a point in time, and the bounds tighten as check
    frequency increases. `last_in_stock_at` is NaT when the product was already
    out at our first-ever observation."""
    cols = ["platform", "location_name", "product_id", "brand", "name",
            "last_in_stock_at", "first_out_at"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    rows = []
    key_cols = ["platform", "location_name", "product_id", "brand", "name"]
    for keys, grp in df.sort_values("fetched_at").groupby(key_cols):
        grp = grp.reset_index(drop=True)
        if not bool(grp.iloc[-1]["is_sold_out"]):
            continue  # not currently sold out
        first_out = grp.iloc[-1]["fetched_at"]
        last_in = None
        for i in range(len(grp) - 1, -1, -1):
            if bool(grp.iloc[i]["is_sold_out"]):
                first_out = grp.iloc[i]["fetched_at"]
            else:
                last_in = grp.iloc[i]["fetched_at"]
                break
        rows.append(dict(zip(key_cols, keys),
                         last_in_stock_at=last_in, first_out_at=first_out))
    return pd.DataFrame(rows, columns=cols)


def oos_hours_by_daypart(df: pd.DataFrame) -> pd.DataFrame:
    """Split each brand's observed sold-out hours into peak (6-11 PM IST) vs
    off-peak, using the same gap-attribution model as stockout_duration_hours()
    (each inter-check gap is counted against the daypart of the check that began
    it), so the two functions' totals reconcile."""
    cols = ["brand", "oos_hours_peak", "oos_hours_offpeak"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    totals: dict[str, list[float]] = {}
    key_cols = ["platform", "location_name", "product_id", "brand", "name"]
    for keys, grp in df.sort_values("fetched_at").groupby(key_cols):
        brand = keys[3]
        peak = offpeak = 0.0
        prev_time = None
        prev_sold_out = False
        for _, row in grp.iterrows():
            if prev_time is not None and prev_sold_out:
                gap = (row["fetched_at"] - prev_time).total_seconds() / 3600
                if PEAK_START_HOUR_IST <= _ist_hour(prev_time) < PEAK_END_HOUR_IST:
                    peak += gap
                else:
                    offpeak += gap
            prev_time = row["fetched_at"]
            prev_sold_out = bool(row["is_sold_out"])
        t = totals.setdefault(brand, [0.0, 0.0])
        t[0] += peak
        t[1] += offpeak

    return pd.DataFrame(
        [{"brand": b, "oos_hours_peak": round(p, 1), "oos_hours_offpeak": round(o, 1)}
         for b, (p, o) in totals.items()]
    )


def depletion_forecast(df: pd.DataFrame, min_points: int = 3) -> pd.DataFrame:
    """Rough "time to stock-out" estimate per (platform, location, product) using the
    recent inventory decline velocity (units/hour) from the last few snapshots,
    excluding restock jumps. This is a heuristic, not a demand model — good enough
    for a pitch demo; production would want a proper model trained on real history.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["platform", "location_name", "brand", "name", "current_inventory",
                     "depletion_rate_per_hr", "est_hours_to_stockout"]
        )

    rows = []
    key_cols = ["platform", "location_name", "product_id", "brand", "name"]
    for keys, grp in df.sort_values("fetched_at").groupby(key_cols):
        grp = grp.reset_index(drop=True)
        if len(grp) < min_points:
            continue
        recent = grp.tail(6).reset_index(drop=True)
        declines = []
        for i in range(1, len(recent)):
            dt_hours = (recent.loc[i, "fetched_at"] - recent.loc[i - 1, "fetched_at"]).total_seconds() / 3600
            d_inv = recent.loc[i - 1, "inventory"] - recent.loc[i, "inventory"]
            if dt_hours > 0 and d_inv > 0:  # ignore restocks / flat periods
                declines.append(d_inv / dt_hours)
        current_inventory = int(recent.iloc[-1]["inventory"])
        if not declines or current_inventory == 0:
            continue
        rate = sum(declines) / len(declines)
        if rate <= 0:
            continue
        est_hours = current_inventory / rate
        rows.append(
            dict(
                zip(key_cols, keys),
                current_inventory=current_inventory,
                depletion_rate_per_hr=round(rate, 2),
                est_hours_to_stockout=round(est_hours, 1),
            )
        )
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("est_hours_to_stockout")
    return result
