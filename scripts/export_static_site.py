"""One-shot script for the scheduled GitHub Actions job (see
.github/workflows/update-data.yml): scrape live Blinkit data, generate Outbox
alerts from the before/after diff, then dump a static JSON snapshot per
tracked brand into docs/data/ for GitHub Pages to serve.

Why this exists: GitHub Pages can only serve static files - there's no
always-on server to call webapp/server.py's live API from. This reuses that
exact same server.py code (build_dashboard, _run_refresh) so the static
snapshots are computed identically to the live API, just pre-baked on a
schedule instead of per-request.

Run with:  python scripts/export_static_site.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webapp"))

from config import CLIENT_BRAND, TRACKED_BRANDS  # noqa: E402
import server as _server  # noqa: E402 (webapp/server.py)

DOCS_DATA = ROOT / "docs" / "data"


def slugify(name: str) -> str:
    """Must match the JS slugify() in docs/js/app.js exactly."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> None:
    print("Running live Blinkit collector...")
    n, n_notifs = _server._run_refresh()
    print(f"Collected {n} rows, {n_notifs} new alert(s).")

    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    brands_out = []
    for brand in TRACKED_BRANDS:
        payload = _server.build_dashboard(brand=brand)
        slug = slugify(brand)
        (DOCS_DATA / f"{slug}.json").write_text(json.dumps(payload))
        brands_out.append({"name": brand, "slug": slug})
        print(f"Wrote data/{slug}.json")

    index = {"defaultSlug": slugify(CLIENT_BRAND), "brands": brands_out}
    (DOCS_DATA / "index.json").write_text(json.dumps(index))
    print("Wrote data/index.json")


if __name__ == "__main__":
    main()
