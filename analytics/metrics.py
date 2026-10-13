"""Core analytics: OOS detection, competitive benchmarking, depletion prediction."""
from __future__ import annotations

import pandas as pd


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
        return pd.DataFrame(columns=["platform", "location_name", "brand", "name", "oos_hours", "oos_episodes"])

    rows = []
    key_cols = ["platform", "location_name", "product_id", "brand", "name"]
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
