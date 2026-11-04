"""SQLite-backed time-series store for product stock snapshots."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from scrapers.base import ProductSnapshot

# Different scrapers/actors report the same brand with inconsistent casing or
# punctuation (e.g. Blinkit vs Zepto vs Instamart), which fragments brand-level
# analytics (availability %, "top competitor", brand counts) into near-duplicate
# buckets. Normalize at read time so it's fixed retroactively for already-collected
# data too, without needing a backfill migration. Keyed by lowercase+stripped name;
# add an entry here whenever you spot a new duplicate variant in the data.
BRAND_ALIASES = {
    "too yumm!": "Too Yumm",
    "too yumm": "Too Yumm",
    "let's try": "Let's Try",
    "yellow diamond": "Yellow Diamond",
}


def _normalize_brand(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        return name
    return BRAND_ALIASES.get(name.strip().lower(), name.strip())

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    location_name TEXT NOT NULL,
    pincode TEXT NOT NULL,
    merchant_id TEXT,
    query TEXT,
    product_id TEXT NOT NULL,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT,
    price REAL,
    mrp REAL,
    inventory INTEGER,
    is_sold_out INTEGER,
    fetched_at TEXT NOT NULL,
    is_synthetic INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_snapshots_lookup
    ON snapshots (platform, location_name, product_id, fetched_at);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    brand TEXT NOT NULL,
    product_name TEXT,
    location_name TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def _connect(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_snapshots(db_path: str, snapshots: Iterable[ProductSnapshot]) -> int:
    rows = [
        (
            s.platform, s.location_name, s.pincode, s.merchant_id, s.query,
            s.product_id, s.brand, s.name, s.unit, s.price, s.mrp,
            s.inventory, int(s.is_sold_out), s.fetched_at, int(s.is_synthetic),
        )
        for s in snapshots
    ]
    if not rows:
        return 0
    with _connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO snapshots
               (platform, location_name, pincode, merchant_id, query, product_id,
                brand, name, unit, price, mrp, inventory, is_sold_out, fetched_at, is_synthetic)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def prune_old_snapshots(db_path: str, days: int = 30) -> int:
    """Deletes snapshot rows older than `days`. Without this, the append-only
    `snapshots` table (and the SQLite file the GitHub Actions workflow commits
    to git every run) would grow forever - every collector run inserts a full
    fresh batch of rows regardless of whether anything changed, with no
    dedup. 30 days is enough history for the trend/depletion-forecast charts
    to mean something, while keeping storage and repo size bounded. Also runs
    VACUUM when rows were actually deleted, so the .db file shrinks back down
    instead of just marking space as reusable internally.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM snapshots WHERE fetched_at < ?", (cutoff,))
        deleted = cur.rowcount
        if deleted > 0:
            conn.commit()  # VACUUM can't run inside a pending transaction
            conn.execute("VACUUM")
    return deleted


def load_snapshots(db_path: str) -> pd.DataFrame:
    with _connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM snapshots", conn)
    if not df.empty:
        df["fetched_at"] = pd.to_datetime(df["fetched_at"])
        df["is_sold_out"] = df["is_sold_out"].astype(bool)
        df["is_synthetic"] = df["is_synthetic"].astype(bool)
        df["brand"] = df["brand"].map(_normalize_brand)
    return df


def save_notifications(db_path: str, notifications: Iterable[dict]) -> int:
    """notifications: list of dicts with keys type, severity, brand, product_name,
    location_name, message, created_at (ISO string)."""
    rows = [
        (n["type"], n["severity"], n["brand"], n.get("product_name"), n.get("location_name"),
         n["message"], n["created_at"])
        for n in notifications
    ]
    if not rows:
        return 0
    with _connect(db_path) as conn:
        conn.executemany(
            """INSERT INTO notifications
               (type, severity, brand, product_name, location_name, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def load_notifications(db_path: str) -> pd.DataFrame:
    with _connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM notifications ORDER BY created_at DESC", conn)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def export_to_excel(db_path: str, out_path: str) -> int:
    """Mirrors the full `snapshots` + `notifications` history (the complete
    30-day SQLite retention, not just the dashboard's narrower UI_WINDOW_DAYS -
    see config.py) into a human-readable .xlsx with one sheet each. Called
    after every collector run so the file is always a complete, current copy -
    overwritten wholesale each time rather than appended, since Excel has no
    safe concurrent-append story and SQLite is already the real source of
    truth. Returns the row count written to the snapshots sheet.
    """
    snaps = load_snapshots(db_path)
    notifs = load_notifications(db_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Excel can't hold timezone-aware datetimes at all (raises on write) - keep
    # the original UTC ISO string (matches the raw SQLite column exactly) and
    # add a separate naive IST column for human readability, rather than
    # silently reinterpreting/losing the timezone.
    def _with_ist(df: pd.DataFrame, col: str) -> pd.DataFrame:
        if df.empty or col not in df.columns:
            return df
        df = df.copy()
        df[f"{col}_utc"] = df[col].astype(str)
        df[f"{col}_ist"] = df[col].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return df.drop(columns=[col])

    snaps_out = _with_ist(snaps, "fetched_at")
    snaps_out = snaps_out.sort_values("fetched_at_utc", ascending=False) if not snaps_out.empty else snaps_out
    notifs_out = _with_ist(notifs, "created_at")

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        snaps_out.to_excel(writer, sheet_name="snapshots", index=False)
        notifs_out.to_excel(writer, sheet_name="notifications", index=False)
    return len(snaps)
