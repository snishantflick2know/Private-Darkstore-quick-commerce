"""Streamlit pitch-demo dashboard: Gurgaon namkeen stock intelligence for Haldiram's.

Run with:  streamlit run app/dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.metrics import (
    availability_by,
    availability_by_brand,
    current_oos_alerts,
    depletion_forecast,
    latest_snapshot,
    location_summary,
    previous_snapshot,
    stockout_duration_hours,
)
from config import CLIENT_BRAND, DB_PATH, GURGAON_LOCATIONS, TRACKED_BRANDS
from map_render import render_location_map
from storage.db import init_db, load_snapshots
from theme import PLATFORM_COLORS, _html, apply_layout, card_header, delta_chip, dot_legend, inject_css, kpi_card


def card_header_with_download(icon, title, subtitle, tone, df_for_download, filename):
    """Renders a card header with a small functional CSV download button on the right,
    matching the reference dashboard's download-icon-in-card-header pattern.
    """
    hcol, dcol = st.columns([5, 1])
    with hcol:
        st.markdown(card_header(icon, title, subtitle, tone), unsafe_allow_html=True)
    with dcol:
        if not df_for_download.empty:
            st.download_button(
                "⬇ CSV", df_for_download.to_csv(index=False).encode(), file_name=filename,
                mime="text/csv", use_container_width=True,
            )

st.set_page_config(page_title="Namkeen Stock Intelligence — Gurgaon", layout="wide", page_icon="🛒")
st.markdown(inject_css(), unsafe_allow_html=True)

init_db(DB_PATH)
df_all = load_snapshots(DB_PATH)

# ================= Sidebar: brand + filters + data status =================
with st.sidebar:
    st.markdown(
        _html("""
        <div class="sb-brand">
            <div class="sb-brand-badge">🛒</div>
            <div>
                <div class="sb-brand-name">Haldiram Pulse</div>
                <div class="sb-brand-sub">Q-commerce stock intelligence</div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sb-section-label">Refresh</div>', unsafe_allow_html=True)
    st.caption("Blinkit only (free). Zepto/Instamart use paid Apify actors, so that refresh is kept to manual `python collector.py` runs only - never exposed here, to avoid a public visitor accidentally spending your Apify balance.")
    if st.button("🔄 Refresh Blinkit now", use_container_width=True):
        with st.spinner("Pulling live Blinkit data for all tracked locations..."):
            import collector as _collector
            n = _collector.run_once(include_others=False)
        st.success(f"Collected {n} new rows.")
        st.rerun()

    if df_all.empty:
        st.info("No data collected yet - click 'Refresh Blinkit now' above to pull live data.")
    else:
        st.markdown('<div class="sb-section-label">Filters</div>', unsafe_allow_html=True)
        platforms = sorted(df_all["platform"].unique())
        sel_platforms = st.multiselect("Platform", platforms, default=platforms, label_visibility="collapsed", placeholder="Platform")
        locations = sorted(df_all["location_name"].unique())
        sel_locations = st.multiselect("Gurgaon location", locations, default=locations, label_visibility="collapsed", placeholder="Location")
        brands = sorted(df_all["brand"].unique())
        sel_brands = st.multiselect(
            "Brands", brands, default=[b for b in TRACKED_BRANDS if b in brands] or brands,
            label_visibility="collapsed", placeholder="Brands",
        )
        live_only = st.checkbox(
            "Live data only", value=True,
            help="ON by default so KPIs/charts reflect only real scraped data, not seeded demo history. "
                 "Turn off to see trend/forecast charts, which need the seeded history to have anything to show.",
        )

        st.markdown('<div class="sb-section-label">Data freshness</div>', unsafe_allow_html=True)
        counts = df_all.groupby(["platform", "is_synthetic"]).size().unstack(fill_value=0)
        for p in counts.index:
            live_n = int(counts.loc[p, False]) if False in counts.columns else 0
            synth_n = int(counts.loc[p, True]) if True in counts.columns else 0
            dot = "🟢" if live_n > 0 else "🟡"
            st.markdown(
                f'<div class="sb-status-row">{dot} <b>{p.capitalize()}</b> &nbsp;{live_n} live / {synth_n} sim</div>',
                unsafe_allow_html=True,
            )

if df_all.empty:
    st.warning(
        "No data yet. Run `python collector.py` to pull live Blinkit data, and/or "
        "`python seed_history.py` to backfill demo trend history."
    )
    st.stop()

# ================= Top toolbar =================
live_by_platform = (~df_all["is_synthetic"]).groupby(df_all["platform"]).any()
platform_pills = "".join(
    f'<span class="pill {"pill-live" if live_by_platform.get(p, False) else "pill-sim"}">'
    f'{"●" if live_by_platform.get(p, False) else "◐"} {"Live" if live_by_platform.get(p, False) else "No live data"} · {p.capitalize()}</span>'
    for p in sorted(df_all["platform"].unique())
)
tcol1, tcol2 = st.columns([3, 1.3])
with tcol1:
    st.markdown('<p class="toolbar-title">🛒 Quick-Commerce Namkeen Stock Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="toolbar-sub">Built for Haldiram\'s — shelf availability, competitive benchmarking & stock-out risk across Gurgaon dark stores</p>', unsafe_allow_html=True)
with tcol2:
    st.markdown(f'<div style="text-align:right; padding-top:6px">{platform_pills}</div>', unsafe_allow_html=True)

st.write("")

df = df_all[
    df_all["platform"].isin(sel_platforms)
    & df_all["location_name"].isin(sel_locations)
    & df_all["brand"].isin(sel_brands)
]
if live_only:
    df = df[~df["is_synthetic"]]

if df.empty:
    st.info("No rows match the current filters.")
    st.stop()

latest = latest_snapshot(df)

# ================= Top-line KPIs =================
haldiram_latest = latest[latest["brand"] == CLIENT_BRAND]
avail = availability_by_brand(df)

oos_now = haldiram_latest[haldiram_latest["is_sold_out"]]
h_avail = avail[avail["brand"] == CLIENT_BRAND]["availability_pct"].mean()
non_client = avail[avail["brand"] != CLIENT_BRAND]
best_competitor = (
    non_client.groupby("brand")["availability_pct"].mean().idxmax() if not non_client.empty else "—"
)

# Real "vs previous check" deltas - only computed when a prior collector round
# actually exists for the current filter set, never fabricated.
prev = previous_snapshot(df)
oos_delta_html, avail_delta_html = "", ""
oos_meta, avail_meta = f"of {len(haldiram_latest)} store-SKU pairs tracked", "share of checks found in stock"
if not prev.empty:
    prev_haldiram = prev[prev["brand"] == CLIENT_BRAND]
    if not prev_haldiram.empty:
        prev_oos_n = int(prev_haldiram["is_sold_out"].sum())
        oos_delta_html = delta_chip(len(oos_now) - prev_oos_n, suffix="", higher_is_bad=True)
        oos_meta = f"vs previous check ({prev_oos_n} then)"
        prev_avail = (1 - prev_haldiram["is_sold_out"].mean()) * 100
        if pd.notna(h_avail):
            avail_delta_html = delta_chip(h_avail - prev_avail, suffix="pp", higher_is_bad=False)
            avail_meta = f"vs previous check ({prev_avail:.0f}% then)"

total_stores = df["location_name"].nunique()
total_brands = df["brand"].nunique()
platform_icons = {"blinkit": "🟢", "zepto": "🟣", "instamart": "🟠"}

PRODUCT_COLS = ["platform", "location_name", "brand", "name", "unit", "price", "inventory", "is_sold_out"]

# Each tile: (icon, title, subtitle, value, meta, delta_html, drill_down_dataframe_or_None).
# The drill-down df is what appears in the "� View details" popover under that tile -
# this is the actual answer to "show me which SKUs and quantities make up this number".
tiles = [
    ("📦", "Haldiram's SKUs", "Across selected stores/platforms",
     str(haldiram_latest["product_id"].nunique()), "No comparison for a count metric", "",
     haldiram_latest[PRODUCT_COLS].sort_values(["platform", "location_name", "name"])),
    ("🚨", "Haldiram's OOS Now", "Currently sold-out store-SKU pairs",
     str(len(oos_now)), oos_meta, oos_delta_html,
     oos_now[PRODUCT_COLS] if not oos_now.empty else None),
    ("📈", "Avg Availability", "Share of checks found in stock",
     f"{h_avail:.0f}%" if pd.notna(h_avail) else "—", avail_meta, avail_delta_html,
     avail[avail["brand"] == CLIENT_BRAND][["platform", "availability_pct", "observations"]]),
    ("🏆", "Top Competitor", "By availability %",
     str(best_competitor), "vs. Haldiram's across tracked brands", "",
     latest[latest["brand"] == best_competitor][PRODUCT_COLS] if best_competitor != "—" else None),
]
for p in sorted(df["platform"].unique()):
    p_avail = avail[(avail["brand"] == CLIENT_BRAND) & (avail["platform"] == p)]["availability_pct"]
    val = f"{p_avail.iloc[0]:.0f}%" if not p_avail.empty else "—"
    n_obs = int(avail[(avail["brand"] == CLIENT_BRAND) & (avail["platform"] == p)]["observations"].sum())
    tiles.append((
        platform_icons.get(p, "🛍️"), f"{p.capitalize()} Availability", "Haldiram's, this platform",
        val, f"{n_obs} checks observed", "",
        haldiram_latest[haldiram_latest["platform"] == p][PRODUCT_COLS],
    ))
tiles.append((
    "🏬", "Stores Monitored", "Gurgaon dark-store catchments", str(total_stores), "in current filter selection", "",
    pd.DataFrame({"location_name": sorted(df["location_name"].unique())}),
))
tiles.append((
    "🏷️", "Brands Compared", "Haldiram's + competitors", str(total_brands), "in current filter selection", "",
    latest.groupby("brand")["product_id"].nunique().reset_index().rename(columns={"product_id": "distinct_skus"}).sort_values("distinct_skus", ascending=False),
))

st.markdown(
    _html(f"""<div class="kpi-row">{''.join(kpi_card(i, t, s, v, m, delta_html=d) for i, t, s, v, m, d, _ in tiles)}</div>"""),
    unsafe_allow_html=True,
)

# Clickable drill-downs, one per tile above (same order). Plain button + session_state
# toggle instead of st.popover - popover's built-in open animation was slow/janky in
# testing, this renders instantly since there's no transition/animation involved at all.
if "open_tile" not in st.session_state:
    st.session_state.open_tile = None

drill_cols = st.columns(len(tiles))
for i, (col, (icon, title, _, _, _, _, _)) in enumerate(zip(drill_cols, tiles)):
    with col:
        if st.button(f"{icon} Details", key=f"detail_btn_{i}", use_container_width=True):
            st.session_state.open_tile = None if st.session_state.open_tile == i else i

if st.session_state.open_tile is not None:
    icon, title, _, _, _, _, drill_df = tiles[st.session_state.open_tile]
    with st.container(border=True):
        close_col, _ = st.columns([6, 1])
        with close_col:
            st.markdown(f"**{icon} {title} — details**")
        if st.button("✕ Close", key="close_drilldown"):
            st.session_state.open_tile = None
            st.rerun()
        if drill_df is None or drill_df.empty:
            st.caption("No matching rows for this tile in the current filters.")
        else:
            st.dataframe(drill_df, use_container_width=True, hide_index=True)

if prev.empty:
    st.caption("ℹ️ Deltas will appear once `collector.py` has run more than once - this is your first recorded check for the current filters.")

# ================= Tabs =================
tab_map, tab_oos, tab_bench, tab_forecast, tab_trend = st.tabs(
    ["🗺️  Map", "🚨  OOS Alerts", "📊  Benchmarking", "🔮  Depletion Forecast", "📈  Trends"]
)

# ---- MAP ----
with tab_map:
    with st.container(border=True):
        st.markdown(card_header("🗺️", "Dark-store health map", "Gurgaon catchments color-coded by overall out-of-stock severity", "indigo"), unsafe_allow_html=True)
        loc_coords = pd.DataFrame(GURGAON_LOCATIONS).rename(columns={"name": "location_name"})[["location_name", "lat", "lon"]]
        summary = location_summary(df, client_brand=CLIENT_BRAND).merge(loc_coords, on="location_name", how="left")

        if summary["lat"].notna().any():
            summary = summary.reset_index(drop=True)
            summary["severity"] = pd.cut(
                summary["oos_pct"], bins=[-1, 10, 30, 100], labels=["Healthy", "Watch", "Critical"]
            ).astype(str)
            summary.insert(0, "#", range(1, len(summary) + 1))

            map_col, legend_col = st.columns([2.2, 1])
            with map_col:
                png_bytes = render_location_map(summary)
                st.image(png_bytes, use_container_width=True)
                st.caption(
                    "Marker size = SKUs tracked at that dark-store catchment. Color = overall OOS severity "
                    "(🟢 <10% OOS, 🟠 10-30%, 🔴 >30%). Numbers match the table →"
                )
            with legend_col:
                st.markdown("**Legend**")
                st.markdown("🟢 Healthy &nbsp; 🟠 Watch &nbsp; 🔴 Critical")
                st.dataframe(
                    summary[["#", "location_name", "severity", "oos_pct", "client_oos_count"]]
                    .rename(columns={"oos_pct": "OOS %", "client_oos_count": "Haldiram's OOS", "severity": "Status"}),
                    use_container_width=True, hide_index=True, height=360,
                    column_config={
                        "OOS %": st.column_config.ProgressColumn("OOS %", min_value=0, max_value=100, format="%.0f%%"),
                    },
                )
            with st.expander("Full location summary table"):
                st.dataframe(summary.drop(columns=["lat", "lon"]), use_container_width=True, hide_index=True)
        else:
            st.info("No coordinates available for the selected locations.")

# ---- OOS ALERTS ----
with tab_oos:
    with st.container(border=True):
        oos = current_oos_alerts(df)
        card_header_with_download("🚨", "Out-of-stock right now", "Latest snapshot per store × SKU, filtered to currently sold-out items", "red", oos, "oos_alerts.csv")
        if oos.empty:
            st.success("✅ No tracked SKUs are currently sold out in the selected filters.")
        else:
            st.dataframe(
                oos[["platform", "location_name", "brand", "name", "unit", "price", "fetched_at", "is_synthetic"]]
                .rename(columns={"is_synthetic": "simulated"}),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "price": st.column_config.NumberColumn("Price", format="₹%.0f"),
                    "fetched_at": st.column_config.DatetimeColumn("Observed at", format="D MMM, h:mm a"),
                },
            )
    st.write("")
    with st.container(border=True):
        st.markdown(card_header("⏱️", "Stock-out frequency & duration", "SKUs that have actually gone out of stock at least once (healthy SKUs with zero stock-outs are not listed here)", "amber"), unsafe_allow_html=True)
        dur = stockout_duration_hours(df)
        if dur.empty:
            st.success("✅ No stock-outs recorded yet for any tracked SKU in the selected filters.")
        else:
            st.dataframe(dur.head(20), use_container_width=True, hide_index=True)

# ---- BENCHMARKING ----
with tab_bench:
    with st.container(border=True):
        card_header_with_download("📊", "Competitive benchmarking", "Availability % split by platform", "purple", avail, "benchmarking.csv")

        view_by = st.radio(
            "View by", options=["Brand", "Location"], horizontal=True, label_visibility="collapsed",
        )
        dim = "brand" if view_by == "Brand" else "location_name"
        bench_df = avail if dim == "brand" else availability_by(df, "location_name")

        st.markdown(
            dot_legend([(p.capitalize(), PLATFORM_COLORS.get(p, "#6b7280")) for p in sorted(bench_df["platform"].unique())]),
            unsafe_allow_html=True,
        )
        fig = px.bar(
            bench_df, x=dim, y="availability_pct", color="platform", barmode="group",
            labels={"availability_pct": "Availability %", dim: ""},
            color_discrete_map=PLATFORM_COLORS, text_auto=".0f",
        )
        fig.update_traces(textfont_size=11, marker_line_width=0)
        apply_layout(fig, yaxis_range=[0, 108], height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Raw availability table"):
            st.dataframe(
                bench_df, use_container_width=True, hide_index=True,
                column_config={
                    "availability_pct": st.column_config.ProgressColumn("Availability %", min_value=0, max_value=100, format="%.0f%%"),
                },
            )

# ---- DEPLETION FORECAST ----
with tab_forecast:
    with st.container(border=True):
        st.markdown(card_header("🔮", "Depletion forecast", "Estimated time to stock-out, based on recent inventory decline velocity", "indigo"), unsafe_allow_html=True)
        st.caption("Heuristic, not a trained demand model - needs real repeated polling history (not a single snapshot) to be meaningful in production.")
        forecast = depletion_forecast(df)
        if forecast.empty:
            st.info("Not enough snapshot history yet to forecast depletion. Keep `collector.py` running on a schedule.")
        else:
            st.dataframe(
                forecast.head(20), use_container_width=True, hide_index=True,
                column_config={
                    "est_hours_to_stockout": st.column_config.NumberColumn("Est. hours to stock-out", format="%.1f h"),
                },
            )

# ---- TRENDS ----
with tab_trend:
    with st.container(border=True):
        st.markdown(card_header("📈", "Inventory trend", "Pick a product to see its inventory level over time", "green"), unsafe_allow_html=True)
        pick_options = (
            latest[["platform", "location_name", "brand", "name", "product_id"]]
            .drop_duplicates()
            .assign(label=lambda d: d["platform"] + " | " + d["location_name"] + " | " + d["brand"] + " - " + d["name"])
        )
        label_to_id = dict(zip(pick_options["label"], pick_options["product_id"]))
        choice = st.selectbox("Product", options=list(label_to_id.keys()))
        if choice:
            pid = label_to_id[choice]
            trend = df[df["product_id"] == pid].sort_values("fetched_at")
            fig2 = px.line(trend, x="fetched_at", y="inventory", markers=True)
            fig2.update_traces(line_color="#4f46e5", line_width=2.5, marker_size=6)
            fig2.add_hline(y=0, line_dash="dot", line_color="#dc2626")
            apply_layout(fig2, height=380, xaxis_title="", yaxis_title="Inventory (units)")
            st.plotly_chart(fig2, use_container_width=True)

st.caption(
    "⚠️ Data sourcing note: Blinkit data is pulled live from an unofficial/reverse-engineered API; "
    "Zepto/Instamart go through third-party Apify actors. None are published partner feeds, and this is "
    "for demo purposes only. A production deployment should use a licensed data partner or a direct "
    "data-sharing agreement with each platform."
)
