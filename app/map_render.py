"""Renders the Gurgaon dark-store map as a static, server-composited PNG.

Why static instead of an interactive Plotly/Mapbox map: Plotly's map renderers
load basemap tiles directly in the browser at view time, and that fails in
sandboxed/locked-down browser environments that block requests to external tile
servers (tile.openstreetmap.org etc). Fetching the tiles server-side once and
baking them into a single PNG avoids any client-side network dependency — the
image is just bytes served by our own Streamlit app.
"""
from __future__ import annotations

import io

import pandas as pd
from PIL import ImageDraw, ImageFont
from staticmap import CircleMarker, StaticMap

from theme import SEVERITY_COLORS


def render_location_map(summary: pd.DataFrame, width: int = 760, height: int = 560) -> bytes:
    """summary must have columns: location_name, lat, lon, skus_tracked, severity.
    Returns PNG bytes with numbered markers (1..N, matching summary row order)
    color-coded by severity and sized by SKU count.
    """
    m = StaticMap(width, height, padding_x=40, padding_y=40)

    max_skus = max(summary["skus_tracked"].max(), 1)
    markers = []
    for _, row in summary.iterrows():
        radius = 14 + int((row["skus_tracked"] / max_skus) * 14)
        color = SEVERITY_COLORS.get(row["severity"], "#2563eb")
        marker = CircleMarker((row["lon"], row["lat"]), color, radius * 2)
        m.add_marker(marker)
        markers.append((row["lon"], row["lat"]))

    image = m.render()

    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    except Exception:
        font = ImageFont.load_default()

    for i, (lon, lat) in enumerate(markers, start=1):
        from staticmap.staticmap import _lat_to_y, _lon_to_x

        px = m._x_to_px(_lon_to_x(lon, m.zoom))
        py = m._y_to_px(_lat_to_y(lat, m.zoom))
        label = str(i)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((px - tw / 2, py - th / 2 - 2), label, fill="white", font=font)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
