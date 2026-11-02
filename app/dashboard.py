"""Streamlit pitch-demo dashboard: live quick-commerce shelf/stock intelligence
for a selectable primary brand vs its tracked competitors, via Blinkit.

Layout follows the "Shelf Pulse" redesign: a left-hand page nav (Overview,
Stock-outs, Competition, Forecast, Alerts) instead of top tabs, DM Sans / violet
visual language, and a big headline availability number on Overview. Every
number on every page is computed from real scraped snapshots - nothing here is
sample/placeholder data, unlike the static design mockup that preceded this.

Run with:  streamlit run app/dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics.metrics import (
    availability_by_brand,
    availability_by_store_brand,
    current_oos_alerts,
    depletion_forecast,
    latest_snapshot,
    location_summary,
    needs_attention,
    oos_summary_stats,
    previous_snapshot,
    stock_on_shelf_by_brand,
    stockout_duration_hours,
)
from analytics.notifications import generate_notifications
from config import CLIENT_BRAND, DB_PATH, GURGAON_LOCATIONS, TRACKED_BRANDS
from map_render import render_location_map
from storage.db import init_db, load_notifications, load_snapshots, save_notifications
from theme import _html, apply_layout, brand_color, card_header, delta_chip, inject_css, kpi_card, status_badge

_TRACKED_LOCATION_NAMES = [loc["name"] for loc in GURGAON_LOCATIONS]
PAGES = ["Overview", "Stock-outs", "Competition", "Forecast", "Alerts"]


def _live_scoped(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df[df["location_name"].isin(_TRACKED_LOCATION_NAMES)]
    return df[~df["is_synthetic"]]


AUTO_REFRESH_MINUTES = 10  # auto-refresh once per browser session if live data is older than this (or missing)


def card_header_with_download(icon, title, subtitle, tone, df_for_download, filename):
    """Renders a card header with a small functional CSV download button on the right."""
    hcol, dcol = st.columns([5, 1])
    with hcol:
        st.markdown(card_header(icon, title, subtitle, tone), unsafe_allow_html=True)
    with dcol:
        if not df_for_download.empty:
            st.download_button(
                "⬇ CSV", df_for_download.to_csv(index=False).encode(), file_name=filename,
                mime="text/csv", use_container_width=True,
            )


def run_blinkit_refresh():
    before_df = _live_scoped(load_snapshots(DB_PATH))
    prev_latest = latest_snapshot(before_df) if not before_df.empty else before_df

    with st.spinner("Pulling live Blinkit data..."):
        import collector as _collector
        n = _collector.run_once()

    after_df = _live_scoped(load_snapshots(DB_PATH))
    new_latest = latest_snapshot(after_df) if not after_df.empty else after_df

    notifs = generate_notifications(prev_latest, new_latest, TRACKED_BRANDS, CLIENT_BRAND)
    if notifs:
        save_notifications(DB_PATH, notifs)

    st.session_state["auto_refreshed_this_session"] = True
    return n, len(notifs)


st.set_page_config(page_title="Shelf Pulse — Stock Intelligence", layout="wide", page_icon="🛒")
st.markdown(inject_css(), unsafe_allow_html=True)

init_db(DB_PATH)
df_all = load_snapshots(DB_PATH)

# Scope is the configured locations only - filter out any leftover rows from
# locations/brands that used to be tracked under a prior configuration, so old
# historical data never leaks into today's KPIs/charts.
if not df_all.empty:
    df_all = df_all[df_all["location_name"].isin(_TRACKED_LOCATION_NAMES)]

# ---- Auto-refresh-if-stale: keeps this feeling genuinely "live" without
# re-scraping on every single widget interaction (Streamlit reruns the whole
# script on every click) - only triggers once per browser session, and only
# when live data is missing or older than AUTO_REFRESH_MINUTES. ----
live_rows = df_all[~df_all["is_synthetic"]] if not df_all.empty else df_all
data_age_minutes = None
if not live_rows.empty:
    data_age_minutes = (pd.Timestamp.now(tz="UTC") - live_rows["fetched_at"].max()).total_seconds() / 60

needs_refresh = data_age_minutes is None or data_age_minutes > AUTO_REFRESH_MINUTES
if needs_refresh and not st.session_state.get("auto_refreshed_this_session", False):
    reason = "no live data yet" if data_age_minutes is None else f"data is {data_age_minutes:.0f} min old"
    st.toast(f"Auto-refreshing Blinkit data ({reason})...", icon="🔄")
    run_blinkit_refresh()
    st.rerun()

# ================= Sidebar: brand + page nav + filters + data status =================
with st.sidebar:
    st.markdown(
        _html("""
        <div class="sb-brand">
            <div class="sb-brand-badge">🛒</div>
            <div>
                <div class="sb-brand-name">Shelf Pulse</div>
                <div class="sb-brand-sub">Sohna Road + Lajpat Nagar · Blinkit · live</div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

if not df_all.empty:
    _available_brands_for_selector = sorted(df_all["brand"].unique())
else:
    _available_brands_for_selector = []
_primary_brand_options = [b for b in TRACKED_BRANDS if b in _available_brands_for_selector] or TRACKED_BRANDS

with st.sidebar:
    if df_all.empty:
        st.info("No data collected yet.")
    else:
        st.markdown('<div class="sb-section-label">Primary brand</div>', unsafe_allow_html=True)
        client_brand = st.selectbox(
            "Primary brand", options=_primary_brand_options,
            index=_primary_brand_options.index(CLIENT_BRAND) if CLIENT_BRAND in _primary_brand_options else 0,
            label_visibility="collapsed",
            help="The brand all pages focus on. Every other tracked brand becomes a competitor it's benchmarked against.",
        )

        st.markdown('<div class="sb-section-label">Pages</div>', unsafe_allow_html=True)
        page = st.radio("Page", PAGES, label_visibility="collapsed")

        st.markdown('<div class="sb-section-label">Filters</div>', unsafe_allow_html=True)
        _all_brands_in_data = set(df_all["brand"].unique())
        brands = [b for b in TRACKED_BRANDS if b in _all_brands_in_data]
        sel_brands = st.multiselect(
            "Brands", brands, default=brands,
            label_visibility="collapsed", placeholder="Brands",
        )
        live_only = st.checkbox(
            "Live data only", value=True,
            help="ON by default so KPIs/charts reflect only real scraped data, not seeded demo history. "
                 "Turn off to see trend/forecast charts, which need the seeded history to have anything to show.",
        )

        st.markdown('<div class="sb-section-label">Data status</div>', unsafe_allow_html=True)
        if data_age_minutes is not None:
            status_line = (
                f"Data is up to date. We check {len(_TRACKED_LOCATION_NAMES)} stores every {AUTO_REFRESH_MINUTES} min."
                if data_age_minutes <= AUTO_REFRESH_MINUTES else
                f"Data is {data_age_minutes:.0f} min old — refreshing shortly."
            )
            st.markdown(f'<div class="sb-status-card">{status_line}<br>Last check: {data_age_minutes:.0f} min ago.</div>', unsafe_allow_html=True)
            st.write("")
        if st.button("🔄 Refresh now", use_container_width=True):
            n, n_notifs = run_blinkit_refresh()
            st.success(f"Collected {n} new rows, {n_notifs} new alert(s) in Alerts.")
            st.rerun()

if df_all.empty:
    st.warning("No data yet. Click 'Refresh now' in the sidebar to pull live Blinkit data.")
    st.stop()

# Always include the selected primary brand in scope, even if it got
# deselected from the "Brands" filter above - the dashboard breaks without it.
_effective_brands = list(set(sel_brands) | {client_brand})
df = df_all[df_all["brand"].isin(_effective_brands)]
if live_only:
    df = df[~df["is_synthetic"]]

if df.empty:
    st.info("No rows match the current filters.")
    st.stop()

latest = latest_snapshot(df)
prev = previous_snapshot(df)
client_latest = latest[latest["brand"] == client_brand]
avail = availability_by_brand(df)
h_avail = avail[avail["brand"] == client_brand]["availability_pct"].mean()

PAGE_META = {
    "Overview": ("How your shelf looks today", "Where you stand right now, across every tracked store"),
    "Stock-outs": ("What's out of stock", "Every currently sold-out product, and whether a nearby store has it"),
    "Competition": ("You vs other brands", "Availability benchmarked against every tracked competitor"),
    "Forecast": ("What runs out next", "Rough estimate of which products are about to sell out"),
    "Alerts": ("Alerts", "Every stockout, restock, new listing and gap we've detected"),
}
page_title, page_sub = PAGE_META[page]

# ================= Top header =================
tcol1, tcol2 = st.columns([3, 1.3])
with tcol1:
    st.markdown(f'<div class="breadcrumb"><b>{client_brand}</b> › {page}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="toolbar-title">{page_title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="toolbar-sub">{page_sub}</p>', unsafe_allow_html=True)
with tcol2:
    pill_cls = "pill-live" if (data_age_minutes is not None and data_age_minutes <= AUTO_REFRESH_MINUTES) else "pill-sim"
    pill_text = f"● Live · updated {data_age_minutes:.0f} min ago" if data_age_minutes is not None else "◐ No live data"
    pill_col, export_col = st.columns([3, 1])
    with pill_col:
        st.markdown(f'<div style="text-align:right; padding-top:10px"><span class="pill {pill_cls}">{pill_text}</span></div>', unsafe_allow_html=True)
    with export_col:
        st.download_button(
            "⬇ Export", df.to_csv(index=False).encode(), file_name=f"shelf_pulse_{page.lower().replace(' ', '_')}.csv",
            mime="text/csv", use_container_width=True,
        )

st.write("")

PRODUCT_COLS = ["location_name", "brand", "name", "unit", "price", "inventory", "is_sold_out"]

# ================= OVERVIEW =================
if page == "Overview":
    stats = oos_summary_stats(df, client_brand)

    # ---- Headline availability ----
    with st.container(border=True):
        hcol, tcol = st.columns([1.3, 2])
        with hcol:
            delta_html, delta_sentence = "", "No prior check yet to compare against."
            if not prev.empty:
                prev_client = prev[prev["brand"] == client_brand]
                if not prev_client.empty and pd.notna(h_avail):
                    prev_avail = (1 - prev_client["is_sold_out"].mean()) * 100
                    d = h_avail - prev_avail
                    delta_html = delta_chip(d, suffix=" pts", higher_is_bad=False)
                    direction = "Up" if d > 0 else ("Down" if d < 0 else "Flat vs")
                    delta_sentence = f"{direction} {abs(d):.0f} points from {prev_avail:.0f}% at the previous check."
            headline_value = f"{h_avail:.0f}%" if pd.notna(h_avail) else "—"
            st.markdown(
                _html(f"""
                <div class="headline-number">{headline_value}</div>
                <div class="headline-sentence">On-shelf availability for <b>{client_brand}</b> across {len(_TRACKED_LOCATION_NAMES)} tracked stores. {delta_sentence}</div>
                """),
                unsafe_allow_html=True,
            )
            if delta_html:
                st.markdown(delta_html, unsafe_allow_html=True)
        with tcol:
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Products in stock", f"{stats['skus_in_stock']} of {stats['skus_tracked']}")
            s2.metric("Hours off shelf", f"{stats['hours_off_shelf']:.0f} hrs")
            s3.metric("Average outage", f"{stats['avg_outage_hours']:.1f} hrs" if stats["avg_outage_hours"] is not None else "—")
            s4.metric("Competitors out of stock", str(stats["competitors_oos_now"]))

    st.write("")

    # ---- Availability over time (real history - may be short if the
    # collector has only run a few times; not fabricated to look like 7 days) ----
    with st.container(border=True):
        st.markdown(card_header("📈", "Availability over time", f"{client_brand} vs tracked competitors, from actual collector runs so far", "indigo"), unsafe_allow_html=True)
        hist = df.copy()
        hist["bucket"] = hist["fetched_at"].dt.floor("h")
        trend = (
            hist.groupby(["bucket", "brand"])
            .agg(stockouts=("is_sold_out", "sum"), observations=("is_sold_out", "size"))
            .reset_index()
        )
        trend["availability_pct"] = (1 - trend["stockouts"] / trend["observations"]) * 100
        if trend["bucket"].nunique() < 2:
            st.info("Only one collector run so far for the current filters - the trend line will fill in as more live checks happen over time.")
        else:
            fig = go.Figure()
            for b in sorted(trend["brand"].unique()):
                bd = trend[trend["brand"] == b].sort_values("bucket")
                fig.add_trace(go.Scatter(
                    x=bd["bucket"], y=bd["availability_pct"], mode="lines+markers", name=b,
                    line=dict(width=3 if b == client_brand else 1.6, color=brand_color(b, client_brand)),
                ))
            apply_layout(fig, height=360, yaxis_title="Availability %", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    st.write("")

    col_a, col_b = st.columns([1.3, 1])
    with col_a:
        with st.container(border=True):
            st.markdown(card_header("📦", "Stock on shelf", "Total units currently on shelf per brand, across tracked stores", "purple"), unsafe_allow_html=True)
            shelf = stock_on_shelf_by_brand(df)
            if shelf.empty:
                st.info("No inventory data yet.")
            else:
                fig2 = px.bar(
                    shelf, x="units", y="brand", orientation="h",
                    text=shelf["units"].map(lambda u: f"{u:,.0f}"),
                    color="brand", color_discrete_map={b: brand_color(b, client_brand) for b in shelf["brand"]},
                )
                fig2.update_traces(textposition="outside")
                apply_layout(fig2, height=280, showlegend=False, yaxis_title="", xaxis_title="Units")
                st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        with st.container(border=True):
            st.markdown(card_header("🚨", "Needs your attention", f"{client_brand}'s worst current stock-outs, by time off shelf", "red"), unsafe_allow_html=True)
            attn = needs_attention(df, client_brand)
            if attn.empty:
                st.success(f"✅ No {client_brand} SKUs are currently sold out.")
            else:
                for _, row in attn.iterrows():
                    st.markdown(
                        _html(f"""
                        <div class="attn-card">
                            <div><div class="attn-text">{row['name']} — {row['location_name']}</div>
                            <div class="attn-sub">Out {row['oos_hours']:.1f} hrs so far, {int(row['oos_episodes'])} episode(s)</div></div>
                        </div>
                        """),
                        unsafe_allow_html=True,
                    )
                st.caption("Open **Stock-outs** to check nearby-store availability for these.")

    st.write("")

    with st.container(border=True):
        st.markdown(card_header("🏬", "Availability by store", f"{client_brand}'s on-shelf rate at each tracked store, vs every tracked competitor there", "indigo"), unsafe_allow_html=True)
        store_brand = availability_by_store_brand(df)
        if store_brand.empty:
            st.info("No store-level data yet.")
        else:
            pivot = store_brand.pivot(index="location_name", columns="brand", values="availability_pct").round(0)
            cols = [c for c in [client_brand] + [b for b in pivot.columns if b != client_brand] if c in pivot.columns]
            pivot = pivot[cols]

            def _cell_tone(v):
                if pd.isna(v):
                    return "#F2F4F7", "#98A2B3"
                if v >= 90:
                    return "#ECFDF3", "#079455"
                if v >= 80:
                    return "#FFFAEB", "#DC6803"
                return "#FEF3F2", "#D92D20"

            header_cells = "".join(
                f'<th style="padding:8px 10px;text-align:center;{"border-bottom:2px solid " + brand_color(c, client_brand) + ";" if c == client_brand else ""}">{c}</th>'
                for c in cols
            )
            body_rows = []
            for loc, row in pivot.iterrows():
                cells = []
                for c in cols:
                    v = row[c]
                    bg, fg = _cell_tone(v)
                    outline = f"outline:2px solid {brand_color(c, client_brand)};outline-offset:-2px;" if c == client_brand else ""
                    label = f"{v:.0f}%" if pd.notna(v) else "—"
                    cells.append(f'<td style="padding:0;"><div style="height:44px;border-radius:8px;background:{bg};color:{fg};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.82rem;{outline}">{label}</div></td>')
                body_rows.append(f'<tr><td style="padding:8px 10px;font-weight:600;font-size:0.84rem;color:#0D0F12;white-space:nowrap;">{loc}</td>{"".join(cells)}</tr>')

            grid_html = f"""
            <table style="width:100%;border-collapse:separate;border-spacing:4px 4px;">
                <thead><tr><th></th>{header_cells}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
            """
            st.markdown(_html(grid_html), unsafe_allow_html=True)
            st.caption("🟢 90%+ Healthy · 🟠 80-89% Watch · 🔴 under 80% Critical. The outlined column is your (primary) brand.")

# ================= STOCK-OUTS =================
elif page == "Stock-outs":
    oos = current_oos_alerts(df)
    client_oos = oos[oos["brand"] == client_brand] if not oos.empty else oos
    competitor_oos = oos[oos["brand"] != client_brand] if not oos.empty else oos

    with st.container(border=True):
        card_header_with_download("🚨", "Out of stock right now", f"{client_brand}'s currently sold-out products, latest check per store", "red", client_oos, "out_of_stock.csv")
        if client_oos.empty:
            st.success(f"✅ No {client_brand} products are currently sold out in the selected filters.")
        else:
            st.dataframe(
                client_oos[["location_name", "name", "unit", "price", "fetched_at"]]
                .rename(columns={"fetched_at": "Observed at"}),
                use_container_width=True, hide_index=True,
                column_config={
                    "price": st.column_config.NumberColumn("Price", format="₹%.0f"),
                    "Observed at": st.column_config.DatetimeColumn("Observed at", format="D MMM, h:mm a"),
                },
            )

    st.write("")
    with st.container(border=True):
        st.markdown(
            card_header("🔎", "Check nearby stores", f"For {client_brand}'s currently out-of-stock products, check if a nearby Blinkit dark store has them in stock — a stockout at the nearest store doesn't always mean the area is actually out (validated finding: a secondary store had 6 units while the primary had 0). This runs on demand, not automatically, to respect Blinkit's rate limits.", "indigo"),
            unsafe_allow_html=True,
        )
        if client_oos.empty:
            st.info(f"No {client_brand} products are currently out of stock, nothing to check.")
        else:
            st.caption(f"{len(client_oos)} {client_brand} product(s) out of stock. This checks each against up to 3 nearby stores (slow — ~1 request/second to avoid rate limits).")
            if st.button("🔍 Check nearby stores now", key="check_nearby_stores"):
                from scrapers.blinkit import BlinkitScraper, RateLimitedError
                import time as _time

                loc_lookup = {loc["name"]: (loc["lat"], loc["lon"]) for loc in GURGAON_LOCATIONS}
                scraper = BlinkitScraper()
                results = []
                with st.spinner("Checking nearby stores..."):
                    for _, row in client_oos.iterrows():
                        loc_name = row["location_name"]
                        if loc_name not in loc_lookup:
                            continue
                        lat, lon = loc_lookup[loc_name]
                        try:
                            merchants = scraper.get_merchants(lat, lon)
                        except Exception:
                            continue
                        for m in merchants[1:4]:
                            _time.sleep(1.0)
                            try:
                                alt = scraper.get_product_at_merchant(
                                    row["product_id"], m["id"], lat, lon, loc_name, row.get("pincode", ""),
                                )
                            except RateLimitedError:
                                results.append({"Product": row["name"], "Location": loc_name, "Store": m["id"], "Result": "⚠️ check failed (rate limited)"})
                                continue
                            if alt is None:
                                results.append({"Product": row["name"], "Location": loc_name, "Store": m["id"], "Result": "Not sold at this store"})
                            elif alt.is_sold_out:
                                results.append({"Product": row["name"], "Location": loc_name, "Store": m["id"], "Result": "Also sold out"})
                            else:
                                results.append({"Product": row["name"], "Location": loc_name, "Store": m["id"], "Result": f"✅ In stock — {alt.inventory} units"})
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                else:
                    st.info("No nearby stores found to check.")

    st.write("")
    with st.container(border=True):
        st.markdown(card_header("⏱️", "Stock-out frequency & duration", f"{client_brand} products that have actually gone out of stock at least once", "amber"), unsafe_allow_html=True)
        dur = stockout_duration_hours(df[df["brand"] == client_brand])
        if dur.empty:
            st.success(f"✅ No stock-outs recorded yet for any tracked {client_brand} product.")
        else:
            st.dataframe(
                dur.head(20).rename(columns={"oos_hours": "Out for (hrs)", "oos_episodes": "Times this week"}),
                use_container_width=True, hide_index=True,
            )

    st.write("")
    with st.container(border=True):
        st.markdown(card_header("🏆", "Where competitors ran out", "Competitor products currently sold out — a gap you may be able to win", "green"), unsafe_allow_html=True)
        if competitor_oos.empty:
            st.info("No tracked competitor is currently out of stock in the selected filters.")
        else:
            st.dataframe(
                competitor_oos[["brand", "location_name", "name", "unit", "price", "fetched_at"]]
                .rename(columns={"fetched_at": "Observed at"}),
                use_container_width=True, hide_index=True,
                column_config={
                    "price": st.column_config.NumberColumn("Price", format="₹%.0f"),
                    "Observed at": st.column_config.DatetimeColumn("Observed at", format="D MMM, h:mm a"),
                },
            )

# ================= COMPETITION =================
elif page == "Competition":
    with st.container(border=True):
        card_header_with_download("📊", "Competitive benchmarking", "Availability % by brand across tracked stores", "purple", avail, "benchmarking.csv")
        fig = px.bar(
            avail, x="brand", y="availability_pct",
            labels={"availability_pct": "Availability %", "brand": ""},
            color="brand", color_discrete_map={b: brand_color(b, client_brand) for b in avail["brand"]},
            text_auto=".0f",
        )
        fig.update_traces(textfont_size=11, marker_line_width=0)
        apply_layout(fig, yaxis_range=[0, 108], height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        bench = avail.copy()
        bench["vs_client"] = bench["availability_pct"] - h_avail
        bench = bench.sort_values("availability_pct", ascending=False)

        def _vs_label(row):
            if row["brand"] == client_brand:
                return "—"
            d = row["vs_client"]
            return f"{abs(d):.0f} ahead" if d > 0 else (f"{abs(d):.0f} behind" if d < 0 else "Even")

        bench["vs you"] = bench.apply(_vs_label, axis=1)
        with st.expander("Comparison table"):
            st.dataframe(
                bench[["brand", "platform", "availability_pct", "observations", "vs you"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "availability_pct": st.column_config.ProgressColumn("Availability %", min_value=0, max_value=100, format="%.0f%%"),
                },
            )

    st.write("")
    with st.container(border=True):
        st.markdown(card_header("🚨", "Competitor stock-outs", "Tracked competitors currently sold out, right now", "red"), unsafe_allow_html=True)
        oos = current_oos_alerts(df)
        competitor_oos = oos[oos["brand"] != client_brand] if not oos.empty else oos
        if competitor_oos.empty:
            st.info("No tracked competitor is currently out of stock.")
        else:
            st.dataframe(
                competitor_oos[["brand", "location_name", "name", "unit", "price"]],
                use_container_width=True, hide_index=True,
                column_config={"price": st.column_config.NumberColumn("Price", format="₹%.0f")},
            )

# ================= FORECAST =================
elif page == "Forecast":
    with st.container(border=True):
        st.markdown(card_header("🔮", "What runs out next", "Estimated time to stock-out, based on recent inventory decline velocity", "indigo"), unsafe_allow_html=True)
        st.caption("Rough estimate, not a trained demand model — needs real repeated polling history (not a single snapshot) to be meaningful in production.")
        forecast = depletion_forecast(df[df["brand"] == client_brand])
        if forecast.empty:
            st.info("Not enough snapshot history yet to forecast depletion. Keep refreshing over time to build history.")
        else:
            forecast = forecast.copy()

            def _action(hrs):
                if hrs <= 6:
                    return "🔴 Reorder now"
                if hrs <= 12:
                    return "🟠 Reorder today"
                return "🟢 On track"

            forecast["action"] = forecast["est_hours_to_stockout"].apply(_action)
            st.dataframe(
                forecast.head(20)[["location_name", "name", "current_inventory", "depletion_rate_per_hr", "est_hours_to_stockout", "action"]]
                .rename(columns={
                    "current_inventory": "Units left", "depletion_rate_per_hr": "Selling (units/hr)",
                    "est_hours_to_stockout": "Time left (hrs)", "name": "Product", "location_name": "Location",
                }),
                use_container_width=True, hide_index=True,
                column_config={"Time left (hrs)": st.column_config.NumberColumn("Time left (hrs)", format="%.1f h")},
            )

    st.write("")
    with st.container(border=True):
        st.markdown(card_header("🗺️", "Store health", "Tracked locations, color-coded by overall out-of-stock severity", "slate"), unsafe_allow_html=True)
        loc_coords = pd.DataFrame(GURGAON_LOCATIONS).rename(columns={"name": "location_name"})[["location_name", "lat", "lon"]]
        summary = location_summary(df, client_brand=client_brand).merge(loc_coords, on="location_name", how="left")
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
                st.caption("Marker size = products tracked. Color = overall OOS severity. The translucent circle is illustrative only, not to scale — not a real delivery-radius boundary.")
            with legend_col:
                st.markdown("**Legend**")
                st.markdown("🟢 Healthy &nbsp; 🟠 Watch &nbsp; 🔴 Critical")
                st.dataframe(
                    summary[["#", "location_name", "severity", "oos_pct", "client_oos_count"]]
                    .rename(columns={"oos_pct": "OOS %", "client_oos_count": f"{client_brand}'s OOS", "severity": "Status"}),
                    use_container_width=True, hide_index=True, height=200,
                    column_config={"OOS %": st.column_config.ProgressColumn("OOS %", min_value=0, max_value=100, format="%.0f%%")},
                )
        else:
            st.info("No coordinates available for the selected locations.")

# ================= ALERTS =================
elif page == "Alerts":
    with st.container(border=True):
        card_header_with_download(
            "📬", "Alerts", "Every alert that would have been sent (stockouts, restocks, low-stock, new products, delistings) - logged here instead of emailed/Slacked, so no external integration is needed for the demo.",
            "amber", load_notifications(DB_PATH), "alerts.csv",
        )
        notif_df = load_notifications(DB_PATH)
        if notif_df.empty:
            st.info("No alerts yet. They're generated automatically every time live data is refreshed (compares the new scrape against the previous one).")
        else:
            sev_icon = {"critical": "🔴", "warning": "🟠", "good": "🟢", "info": "🔵"}
            notif_types = sorted(notif_df["type"].unique())
            sel_types = st.multiselect("Alert type", notif_types, default=notif_types, label_visibility="collapsed", placeholder="Filter by alert type")
            shown = notif_df[notif_df["type"].isin(sel_types)] if sel_types else notif_df
            st.caption(f"{len(shown)} of {len(notif_df)} alerts shown")
            for _, row in shown.head(100).iterrows():
                icon = sev_icon.get(row["severity"], "⚪")
                ts = row["created_at"].strftime("%d %b, %I:%M %p")
                st.markdown(f"{icon} **{ts}** — {row['message']}")

st.write("")
st.caption(
    "⚠️ Data sourcing note: Blinkit data is pulled live from an unofficial/reverse-engineered API, "
    "not a published partner feed, and is for demo purposes only. A production deployment should use "
    "a licensed data partner or a direct data-sharing agreement with Blinkit."
)
