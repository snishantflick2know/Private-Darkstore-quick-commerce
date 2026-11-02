"""Generates "Outbox" notification entries by diffing two snapshot rounds.

This is the alerting layer: instead of integrating with email/Slack/WhatsApp
(extra setup, extra cost, extra things to break), every alert that WOULD have
been sent is just logged to a local "Outbox" table and shown in the dashboard.
Swapping in a real notification channel later is a small, isolated change -
just call out to it wherever `save_notifications` is called here.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

LOW_STOCK_THRESHOLD = 5


def generate_notifications(
    prev_latest: pd.DataFrame, new_latest: pd.DataFrame, tracked_brands: list[str], client_brand: str,
) -> list[dict]:
    """Diffs the previous "latest snapshot" state against the new one and returns
    a list of notification dicts ready for `storage.db.save_notifications`.

    Detects, scoped to tracked_brands only:
      - stockout: a SKU that was in stock and is now sold out
      - restock: a SKU that was sold out and is now back in stock
      - low_stock: a SKU newly at/under LOW_STOCK_THRESHOLD units (client brand only)
      - new_sku: a SKU that appears now but wasn't seen in the previous round
      - delisting: a SKU that was seen before but is now completely gone (not
        just sold out - genuinely absent from search results)
    """
    now = datetime.now(timezone.utc).isoformat()
    notifications: list[dict] = []

    prev_tracked = prev_latest[prev_latest["brand"].isin(tracked_brands)] if not prev_latest.empty else prev_latest
    new_tracked = new_latest[new_latest["brand"].isin(tracked_brands)] if not new_latest.empty else new_latest

    key_cols = ["location_name", "product_id"]
    prev_by_key = {tuple(r[k] for k in key_cols): r for _, r in prev_tracked.iterrows()} if not prev_tracked.empty else {}
    new_by_key = {tuple(r[k] for k in key_cols): r for _, r in new_tracked.iterrows()} if not new_tracked.empty else {}

    for key, new_row in new_by_key.items():
        prev_row = prev_by_key.get(key)
        is_client = new_row["brand"] == client_brand

        if prev_row is None:
            notifications.append({
                "type": "new_sku", "severity": "info", "brand": new_row["brand"],
                "product_name": new_row["name"], "location_name": new_row["location_name"],
                "message": f"New SKU appeared: {new_row['brand']} - {new_row['name']} at {new_row['location_name']}",
                "created_at": now,
            })
            continue

        was_oos, is_oos = bool(prev_row["is_sold_out"]), bool(new_row["is_sold_out"])
        if not was_oos and is_oos:
            notifications.append({
                "type": "stockout", "severity": "critical" if is_client else "warning", "brand": new_row["brand"],
                "product_name": new_row["name"], "location_name": new_row["location_name"],
                "message": f"🚨 OUT OF STOCK: {new_row['brand']} - {new_row['name']} at {new_row['location_name']}",
                "created_at": now,
            })
        elif was_oos and not is_oos:
            notifications.append({
                "type": "restock", "severity": "good", "brand": new_row["brand"],
                "product_name": new_row["name"], "location_name": new_row["location_name"],
                "message": f"✅ Back in stock: {new_row['brand']} - {new_row['name']} at {new_row['location_name']} ({int(new_row['inventory'])} units)",
                "created_at": now,
            })
        elif is_client and not is_oos:
            prev_inv, new_inv = int(prev_row["inventory"]), int(new_row["inventory"])
            if new_inv <= LOW_STOCK_THRESHOLD < prev_inv:
                notifications.append({
                    "type": "low_stock", "severity": "warning", "brand": new_row["brand"],
                    "product_name": new_row["name"], "location_name": new_row["location_name"],
                    "message": f"⚠️ Low stock: {new_row['brand']} - {new_row['name']} at {new_row['location_name']} down to {new_inv} units",
                    "created_at": now,
                })

    for key, prev_row in prev_by_key.items():
        if key not in new_by_key:
            notifications.append({
                "type": "delisting", "severity": "critical" if prev_row["brand"] == client_brand else "info",
                "brand": prev_row["brand"], "product_name": prev_row["name"], "location_name": prev_row["location_name"],
                "message": f"❌ Delisted: {prev_row['brand']} - {prev_row['name']} no longer appears at {prev_row['location_name']}",
                "created_at": now,
            })

    return notifications
