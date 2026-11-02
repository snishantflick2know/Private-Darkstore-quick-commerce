"""Shared visual constants so every chart/card in the dashboard looks consistent.

Visual direction: matches the "Shelf Pulse" redesign handed back by the design
agent (DM Sans typeface, violet #6E5BFF accent, white cards on a light-gray
canvas, left-hand page nav, sentence-case copy, per-brand fixed colors).
"""
from __future__ import annotations

# Rough approximations of each platform's own brand color - makes the dashboard
# instantly scannable to anyone who recognizes the apps.
PLATFORM_COLORS = {
    "blinkit": "#0C831F",
    "zepto": "#8025FB",
    "instamart": "#FC8019",
}

SEVERITY_COLORS = {"Healthy": "#079455", "Watch": "#DC6803", "Critical": "#D92D20"}

ACCENT = "#6E5BFF"
INK = "#0D0F12"
TEXT_SECONDARY = "#344054"
MUTED = "#475467"
MUTED_LIGHT = "#667085"
BORDER = "#EAECF0"
INPUT_BORDER = "#D0D5DD"
SURFACE = "#FFFFFF"
CANVAS = "#F5F6F8"
# Left nav is white by default per the redesign (not a dark navy panel like the
# earlier version of this dashboard) - a dark theme was proposed as optional,
# behind a toggle, but isn't implemented here (Streamlit's own light/dark theme
# switch covers that need instead - see the "☾" note in inject_css).
SIDEBAR_BG = "#FFFFFF"
SIDEBAR_BG_ALT = "#F9FAFB"
SIDEBAR_TEXT = TEXT_SECONDARY
SIDEBAR_MUTED = MUTED_LIGHT

# Fixed per-brand colors so a brand keeps the same color everywhere (bar
# charts, line charts, store grid) instead of a different hue per chart.
BRAND_COLORS = {
    "Real": "#0D9488",
    "Raw Pressery": "#2563EB",
    "B Natural": "#DB2777",
    "Tropicana": "#98A2B3",
}
CLIENT_COLOR = ACCENT  # the selected primary brand always gets the accent color

# (background tint, foreground) pairs for icon badges / accents, by semantic tone.
TONES = {
    "indigo": ("#F4F3FF", "#6E5BFF"),
    "red": ("#FEF3F2", "#D92D20"),
    "green": ("#ECFDF3", "#079455"),
    "amber": ("#FFFAEB", "#DC6803"),
    "purple": ("#F4F3FF", "#5925DC"),
    "slate": ("#F2F4F7", "#344054"),
}

FONT_FAMILY = "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def _html(s: str) -> str:
    """Collapses an HTML/CSS block to a single line before handing it to st.markdown.

    Streamlit runs st.markdown content through a Markdown-to-HTML parser before
    inserting it (even with unsafe_allow_html=True), and multi-line blocks -
    especially ones containing blank lines, like a <style> block with spaced-out
    rule groups - can get misdetected as a code block or split into multiple HTML
    blocks, which then renders as visible literal text instead of being applied as
    actual CSS/markup. Flattening to one line sidesteps all of that ambiguity;
    whitespace is not significant in HTML/CSS outside of <pre>/<code>, so this is safe.
    """
    return " ".join(line.strip() for line in s.splitlines() if line.strip())


PLOTLY_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, size=13, color=INK),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    title_font_size=16,
)


def apply_layout(fig, **overrides):
    layout = {**PLOTLY_LAYOUT, **overrides}
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, linecolor=BORDER)
    fig.update_yaxes(showgrid=True, gridcolor="#F2F4F7", zeroline=False)
    return fig


def brand_color(brand: str, client_brand: str) -> str:
    if brand == client_brand:
        return CLIENT_COLOR
    return BRAND_COLORS.get(brand, "#98A2B3")


def inject_css() -> str:
    return _html(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] {{ font-family: {FONT_FAMILY}; font-variant-numeric: tabular-nums; }}
    .block-container {{ padding-top: 0.8rem; padding-bottom: 1.5rem; max-width: 1480px; }}
    /* Hide the "Deploy"/menu chrome, but NOT the whole header - the sidebar's
       collapse/expand arrow (data-testid="collapsedControl") lives inside that
       same header element, so hiding it entirely traps the sidebar closed with
       no way to reopen it. Target only the specific unwanted pieces instead. */
    #MainMenu, [data-testid="stToolbarActions"], [data-testid="stDecoration"], footer {{
        display: none !important;
    }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    [data-testid="collapsedControl"] {{ display: flex !important; visibility: visible !important; }}
    body {{ background: {CANVAS}; }}
    div[data-testid="stVerticalBlock"] {{ gap: 0.5rem; }}

    /* ---- Top toolbar ---- */
    .toolbar-title {{ font-size: 1.35rem; font-weight: 700; color: {INK}; letter-spacing: -0.01em; margin: 0; }}
    .toolbar-sub {{ font-size: 0.82rem; color: {MUTED}; margin-top: 2px; }}
    .breadcrumb {{ font-size: 0.78rem; color: {MUTED_LIGHT}; font-weight: 500; margin-bottom: 2px; }}
    .breadcrumb b {{ color: {INK}; font-weight: 600; }}
    .pill {{
        display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:999px;
        font-size:0.68rem; font-weight:600; margin-right:5px; letter-spacing:0.01em;
        border: 1px solid transparent;
    }}
    .pill-live {{ background:#ECFDF3; color:#079455; border-color:#ABEFC6; }}
    .pill-sim {{ background:#FFFAEB; color:#B54708; border-color:#FEDF89; }}
    .dot-ind {{ width:7px; height:7px; border-radius:50%; display:inline-block; }}

    /* ---- Headline number (Overview page) ---- */
    .headline-number {{ font-size: 3.1rem; font-weight: 700; color: {INK}; line-height: 1.0; letter-spacing: -0.02em; }}
    .headline-sentence {{ font-size: 0.92rem; color: {MUTED}; margin-top: 8px; max-width: 520px; }}

    /* ---- KPI / tile cards ---- */
    .kpi-row {{ display:flex; gap:12px; margin-bottom: 12px; flex-wrap: wrap; }}
    .kpi-card {{
        flex: 1 1 200px; background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
        padding: 16px 18px; box-shadow: 0 1px 2px rgba(16,24,40,.04);
    }}
    .kpi-head {{ display:flex; align-items:center; gap:8px; margin-bottom: 10px; }}
    .kpi-icon {{
        width: 26px; height: 26px; border-radius: 8px; display:flex; align-items:center;
        justify-content:center; font-size: 0.78rem; flex-shrink:0; background:#F2F4F7; color:#344054;
    }}
    .kpi-title {{ font-size: 0.78rem; color: {INK}; font-weight: 600; line-height:1.2; }}
    .kpi-subtitle {{ font-size: 0.68rem; color: {MUTED_LIGHT}; margin-top:1px; }}
    .kpi-valrow {{ display:flex; align-items:baseline; gap:7px; flex-wrap:wrap; }}
    .kpi-value {{ font-size: 1.9rem; font-weight: 700; color: {INK}; line-height: 1.05; }}
    .kpi-meta {{ font-size: 0.7rem; color: {MUTED_LIGHT}; margin-top: 5px; }}
    .delta-chip {{
        display:inline-flex; align-items:center; gap:2px; padding:1px 8px; border-radius:999px;
        font-size:0.7rem; font-weight:600;
    }}
    .delta-bad {{ background:#FEF3F2; color:#D92D20; }}
    .delta-good {{ background:#ECFDF3; color:#079455; }}
    .delta-flat {{ background:#F2F4F7; color:#475467; }}

    /* ---- Custom dot legend above charts ---- */
    .dot-legend {{ display:flex; gap:16px; flex-wrap:wrap; margin: 0px 0 8px 0; }}
    .dot-legend span.item {{ display:inline-flex; align-items:center; gap:6px; font-size:0.78rem; color:{MUTED}; font-weight:500; }}
    .dot-legend span.dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}

    /* ---- Card headers (for chart/table sections) ---- */
    .card-header {{ display:flex; align-items:flex-start; gap:10px; margin-bottom: 12px; }}
    .card-icon {{
        width: 32px; height: 32px; border-radius: 10px; display:flex; align-items:center;
        justify-content:center; font-size: 0.95rem; flex-shrink: 0;
    }}
    .card-title {{ font-size: 0.98rem; font-weight: 600; color: {INK}; line-height: 1.3; }}
    .card-subtitle {{ font-size: 0.78rem; color: {MUTED}; margin-top: 2px; }}

    /* ---- Status badges ---- */
    .status-badge {{
        display:inline-flex; align-items:center; gap:5px; height:22px; padding:0 9px; border-radius:6px;
        font-size:0.72rem; font-weight:600;
    }}
    .status-healthy {{ background:#ECFDF3; color:#079455; }}
    .status-watch {{ background:#FFFAEB; color:#DC6803; }}
    .status-critical {{ background:#FEF3F2; color:#D92D20; }}

    /* ---- Needs-attention action cards ---- */
    .attn-card {{
        display:flex; align-items:center; justify-content:space-between; gap:10px;
        border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 14px; margin-bottom: 8px;
        background: {SURFACE};
    }}
    .attn-text {{ font-size: 0.84rem; color: {INK}; font-weight:500; }}
    .attn-sub {{ font-size: 0.72rem; color: {MUTED_LIGHT}; margin-top:2px; }}

    /* ---- View-by pill toggle (st.radio, horizontal) ---- */
    div[role="radiogroup"] {{ gap: 4px; }}
    div[role="radiogroup"] label {{
        background: #F2F4F7; border-radius: 8px; padding: 2px 10px; border: 1px solid {BORDER};
    }}

    /* ---- Bordered containers used as cards ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 16px !important; border-color: {BORDER} !important;
        box-shadow: 0 1px 3px rgba(16,24,40,0.04);
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {{ gap: 0.4rem; }}

    /* ---- Left nav (sidebar) - white, per the redesign (not the earlier dark panel) ---- */
    section[data-testid="stSidebar"] {{ background: {SIDEBAR_BG}; border-right: 1px solid {BORDER}; }}
    section[data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT}; }}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{ color: {INK}; }}
    section[data-testid="stSidebar"] hr {{ border-color: {BORDER}; }}
    .sb-brand {{ display:flex; align-items:center; gap:10px; padding: 6px 0 18px 0; border-bottom: 1px solid {BORDER}; margin-bottom: 4px; }}
    .sb-brand-badge {{
        width:34px; height:34px; border-radius:10px; background:linear-gradient(135deg,#6E5BFF,#9b8cff);
        display:flex; align-items:center; justify-content:center; font-size:1.1rem;
    }}
    .sb-brand-name {{ font-weight:700; color:{INK}; font-size:1.02rem; line-height:1.1; }}
    .sb-brand-sub {{ font-size:0.72rem; color:{SIDEBAR_MUTED}; }}
    .sb-section-label {{
        font-size: 0.68rem; font-weight:600; color:{SIDEBAR_MUTED}; text-transform:uppercase;
        letter-spacing: 0.06em; margin: 18px 0 8px 0;
    }}
    .sb-status-row {{ font-size: 0.82rem; color: {SIDEBAR_TEXT}; padding: 3px 0; }}
    .sb-status-card {{
        background: {SIDEBAR_BG_ALT}; border: 1px solid {BORDER}; border-radius: 10px; padding: 10px 12px;
        font-size: 0.76rem; color: {MUTED}; line-height: 1.4;
    }}
    /* st.radio re-skinned as a left-nav page list, active page = light violet pill */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{ flex-direction: column; gap: 2px; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background: transparent; border: none; padding: 9px 10px; border-radius: 8px; width: 100%;
        font-size: 0.86rem; font-weight: 500; color: {TEXT_SECONDARY};
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: {CANVAS}; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {{
        background: {TONES['indigo'][0]}; color: {ACCENT};
    }}

    /* ---- Misc ---- */
    [data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}

    /* ---- Popovers (KPI drill-downs): kill the slow open/resize animation ---- */
    [data-baseweb="popover"], [data-baseweb="popover"] *,
    [data-testid="stPopoverBody"], [data-testid="stPopoverBody"] * {{
        transition: none !important; animation: none !important;
    }}
    </style>
    """)


def delta_chip(delta: float, suffix: str = "%", higher_is_bad: bool = True, precision: int = 0) -> str:
    """Red/green pill with an arrow, matching the reference dashboard's delta chips.
    `higher_is_bad` flips which direction counts as "bad" (e.g. rising OOS% is bad,
    rising availability% is good).
    """
    if delta == 0:
        return f'<span class="delta-chip delta-flat">No change</span>'
    arrow = "▲" if delta > 0 else "▼"
    is_bad = (delta > 0) if higher_is_bad else (delta < 0)
    cls = "delta-bad" if is_bad else "delta-good"
    return f'<span class="delta-chip {cls}">{arrow} {abs(delta):.{precision}f}{suffix}</span>'


def kpi_card(icon: str, title: str, subtitle: str, value: str, meta: str = "", tone: str = "slate", delta_html: str = "") -> str:
    bg, fg = TONES.get(tone, TONES["slate"])
    valrow = f'<div class="kpi-valrow"><div class="kpi-value">{value}</div>{delta_html}</div>'
    return _html(f"""
    <div class="kpi-card">
        <div class="kpi-head">
            <div class="kpi-icon" style="background:{bg};color:{fg}">{icon}</div>
            <div>
                <div class="kpi-title">{title}</div>
                <div class="kpi-subtitle">{subtitle}</div>
            </div>
        </div>
        {valrow}
        <div class="kpi-meta">{meta}</div>
    </div>
    """)


def status_badge(status: str) -> str:
    cls = {"Healthy": "status-healthy", "Watch": "status-watch", "Critical": "status-critical"}.get(status, "status-healthy")
    dot = {"Healthy": "🟢", "Watch": "🟠", "Critical": "🔴"}.get(status, "")
    return f'<span class="status-badge {cls}">{dot} {status}</span>'


def dot_legend(items: list[tuple[str, str]]) -> str:
    """items: list of (label, hex_color) pairs."""
    spans = "".join(
        f'<span class="item"><span class="dot" style="background:{color}"></span>{label}</span>'
        for label, color in items
    )
    return _html(f'<div class="dot-legend">{spans}</div>')


def card_header(icon: str, title: str, subtitle: str = "", tone: str = "indigo") -> str:
    bg, fg = TONES.get(tone, TONES["indigo"])
    return _html(f"""
    <div class="card-header">
        <div class="card-icon" style="background:{bg};color:{fg}">{icon}</div>
        <div>
            <div class="card-title">{title}</div>
            <div class="card-subtitle">{subtitle}</div>
        </div>
    </div>
    """)


def section_head(title: str, subtitle: str = "") -> str:
    return card_header("📌", title, subtitle, "slate")
