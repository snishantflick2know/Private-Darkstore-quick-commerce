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
from PIL import Image, ImageDraw, ImageFont
from staticmap import CircleMarker, StaticMap
from staticmap.staticmap import _lat_to_y, _lon_to_x

from theme import SEVERITY_COLORS

# CartoDB Voyager would look closer to Google Maps (labeled roads, softer
# palette), but their free tiles now require an API key - not worth adding a
# dependency on a key for a demo. Sticking with OpenStreetMap's standard tiles
# (StaticMap's default, no key needed, verified working).
TILE_URL = "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"

ZONE_RADIUS_PX = 85  # translucent "market coverage area" radius around each store
ZONE_ALPHA = 80  # out of 255 - how see-through the coverage zone fill is


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def render_location_map(summary: pd.DataFrame, width: int = 760, height: int = 560) -> bytes:
    """summary must have columns: location_name, lat, lon, skus_tracked, severity.

    Returns PNG bytes with a translucent color-coded "market coverage" zone per
    store (green/amber/red by OOS severity) plus a solid numbered pin on top,
    sized by SKU count - similar in spirit to a coverage/heat-radius map.
    """
    m = StaticMap(width, height, padding_x=40, padding_y=40, url_template=TILE_URL)

    # Tiny markers purely so StaticMap computes sensible bounds/zoom to fit every
    # point - they get fully painted over by our own translucent zone + pin
    # drawing below, so their own appearance doesn't matter.
    for _, row in summary.iterrows():
        m.add_marker(CircleMarker((row["lon"], row["lat"]), "#ffffff", 2))

    image = m.render().convert("RGBA")

    # --- Layer 1: translucent coverage zones (drawn first, so pins sit on top) ---
    zone_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    zone_draw = ImageDraw.Draw(zone_layer)
    positions = []
    max_skus = max(summary["skus_tracked"].max(), 1)
    for _, row in summary.iterrows():
        px = m._x_to_px(_lon_to_x(row["lon"], m.zoom))
        py = m._y_to_px(_lat_to_y(row["lat"], m.zoom))
        positions.append((px, py, row))
        rgb = _hex_to_rgb(SEVERITY_COLORS.get(row["severity"], "#2563eb"))
        zone_draw.ellipse(
            [px - ZONE_RADIUS_PX, py - ZONE_RADIUS_PX, px + ZONE_RADIUS_PX, py + ZONE_RADIUS_PX],
            fill=(*rgb, ZONE_ALPHA), outline=(*rgb, min(ZONE_ALPHA + 60, 255)), width=2,
        )
    image = Image.alpha_composite(image, zone_layer)

    # --- Layer 2: solid numbered pins on top ---
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    except Exception:
        font = ImageFont.load_default()

    for i, (px, py, row) in enumerate(positions, start=1):
        pin_radius = 14 + int((row["skus_tracked"] / max_skus) * 14)
        color = SEVERITY_COLORS.get(row["severity"], "#2563eb")
        draw.ellipse(
            [px - pin_radius, py - pin_radius, px + pin_radius, py + pin_radius],
            fill=color, outline="white", width=2,
        )
        label = str(i)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((px - tw / 2, py - th / 2 - 2), label, fill="white", font=font)

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
