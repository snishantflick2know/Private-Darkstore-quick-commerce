"""Shared visual constants so every chart/card in the dashboard looks consistent.

Visual direction modeled after modern retail-analytics dashboards (dark sidebar nav,
white icon-badged KPI cards, bordered chart cards with icon headers).
"""
from __future__ import annotations

# Rough approximations of each platform's own brand color - makes the dashboard
# instantly scannable to anyone who recognizes the apps.
PLATFORM_COLORS = {
    "blinkit": "#0C831F",
    "zepto": "#8025FB",
    "instamart": "#FC8019",
}

SEVERITY_COLORS = {"Healthy": "#16a34a", "Watch": "#f59e0b", "Critical": "#dc2626"}

ACCENT = "#4f46e5"
INK = "#111827"
MUTED = "#6b7280"
BORDER = "#e8eaed"
SURFACE = "#ffffff"
CANVAS = "#f6f7fb"
SIDEBAR_BG = "#0b1220"
SIDEBAR_BG_ALT = "#141b2d"
SIDEBAR_TEXT = "#cbd5e1"
SIDEBAR_MUTED = "#6b7a99"

# (background tint, foreground) pairs for icon badges / accents, by semantic tone.
TONES = {
    "indigo": ("#eef2ff", "#4f46e5"),
    "red": ("#fef2f2", "#dc2626"),
    "green": ("#f0fdf4", "#16a34a"),
    "amber": ("#fffbeb", "#d97706"),
    "purple": ("#faf5ff", "#9333ea"),
    "slate": ("#f3f4f6", "#374151"),
}

FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


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
    fig.update_yaxes(showgrid=True, gridcolor="#f0f1f5", zeroline=False)
    return fig


def inject_css() -> str:
    return _html(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] {{ font-family: {FONT_FAMILY}; }}
    .block-container {{ padding-top: 0.8rem; padding-bottom: 1.5rem; max-width: 1440px; }}
    #MainMenu, header[data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], footer {{ display: none !important; }}
    body {{ background: {CANVAS}; }}
    div[data-testid="stVerticalBlock"] {{ gap: 0.5rem; }}

    /* ---- Top toolbar ---- */
    .toolbar-title {{ font-size: 1.18rem; font-weight: 800; color: {INK}; letter-spacing: -0.01em; margin: 0; }}
    .toolbar-sub {{ font-size: 0.8rem; color: {MUTED}; margin-top: 1px; }}
    .pill {{
        display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:999px;
        font-size:0.64rem; font-weight:700; margin-right:5px; letter-spacing:0.02em;
        text-transform: uppercase; border: 1px solid transparent;
    }}
    .pill-live {{ background:#f0fdf4; color:#15803d; border-color:#bbf7d0; }}
    .pill-sim {{ background:#fffbeb; color:#b45309; border-color:#fde68a; }}

    /* ---- KPI cards ---- */
    .kpi-row {{ display:flex; gap:10px; margin-bottom: 12px; flex-wrap: wrap; }}
    .kpi-card {{
        flex: 1 1 165px; background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
        padding: 11px 13px; box-shadow: 0 1px 2px rgba(16,24,40,0.03);
        transition: box-shadow .15s ease, transform .15s ease;
    }}
    .kpi-card:hover {{ box-shadow: 0 8px 18px -8px rgba(16,24,40,0.16); transform: translateY(-1px); }}
    .kpi-head {{ display:flex; align-items:center; gap:7px; margin-bottom: 8px; }}
    .kpi-icon {{
        width: 24px; height: 24px; border-radius: 7px; display:flex; align-items:center;
        justify-content:center; font-size: 0.74rem; flex-shrink:0; background:#f3f4f6; color:#4b5563;
    }}
    .kpi-title {{ font-size: 0.73rem; color: {INK}; font-weight: 700; line-height:1.15; }}
    .kpi-subtitle {{ font-size: 0.63rem; color: {MUTED}; margin-top:0px; }}
    .kpi-valrow {{ display:flex; align-items:baseline; gap:6px; flex-wrap:wrap; }}
    .kpi-value {{ font-size: 1.35rem; font-weight: 800; color: {INK}; line-height: 1.05; }}
    .kpi-meta {{ font-size: 0.65rem; color: {MUTED}; margin-top: 3px; }}
    .delta-chip {{
        display:inline-flex; align-items:center; gap:2px; padding:0px 7px; border-radius:999px;
        font-size:0.68rem; font-weight:700;
    }}
    .delta-bad {{ background:#fef2f2; color:#dc2626; }}
    .delta-good {{ background:#f0fdf4; color:#15803d; }}
    .delta-flat {{ background:#f3f4f6; color:#4b5563; }}

    /* ---- Custom dot legend above charts ---- */
    .dot-legend {{ display:flex; gap:14px; flex-wrap:wrap; margin: 0px 0 4px 0; }}
    .dot-legend span.item {{ display:inline-flex; align-items:center; gap:5px; font-size:0.74rem; color:{MUTED}; font-weight:600; }}
    .dot-legend span.dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}

    /* ---- Card headers (for chart/table sections) ---- */
    .card-header {{ display:flex; align-items:flex-start; gap:10px; margin-bottom: 10px; }}
    .card-icon {{
        width: 30px; height: 30px; border-radius: 9px; display:flex; align-items:center;
        justify-content:center; font-size: 0.92rem; flex-shrink: 0;
    }}
    .card-title {{ font-size: 0.92rem; font-weight: 700; color: {INK}; line-height: 1.25; }}
    .card-subtitle {{ font-size: 0.74rem; color: {MUTED}; margin-top: 0px; }}

    /* ---- View-by pill toggle (st.radio, horizontal) ---- */
    div[role="radiogroup"] {{ gap: 4px; }}
    div[role="radiogroup"] label {{
        background: #f3f4f6; border-radius: 8px; padding: 2px 10px; border: 1px solid {BORDER};
    }}

    /* ---- Bordered containers used as cards ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important; border-color: {BORDER} !important;
        box-shadow: 0 1px 3px rgba(16,24,40,0.04);
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {{ gap: 0.35rem; }}

    /* ---- Tabs ---- */
    div[data-testid="stTabs"] button {{ font-weight: 600; font-size: 0.92rem; }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color: {ACCENT}; }}
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background-color: {ACCENT}; }}

    /* ---- Sidebar: dark branding/status panel ---- */
    section[data-testid="stSidebar"] {{ background: {SIDEBAR_BG}; border-right: 1px solid #1e293b; }}
    section[data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT}; }}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{ color: #ffffff; }}
    section[data-testid="stSidebar"] hr {{ border-color: #1e293b; }}
    .sb-brand {{ display:flex; align-items:center; gap:10px; padding: 6px 0 18px 0; }}
    .sb-brand-badge {{
        width:34px; height:34px; border-radius:10px; background:linear-gradient(135deg,#4f46e5,#8b5cf6);
        display:flex; align-items:center; justify-content:center; font-size:1.1rem;
    }}
    .sb-brand-name {{ font-weight:800; color:#fff; font-size:1.02rem; line-height:1.1; }}
    .sb-brand-sub {{ font-size:0.72rem; color:{SIDEBAR_MUTED}; }}
    .sb-section-label {{
        font-size: 0.68rem; font-weight:700; color:{SIDEBAR_MUTED}; text-transform:uppercase;
        letter-spacing: 0.06em; margin: 18px 0 8px 0;
    }}
    .sb-status-row {{ font-size: 0.82rem; color: {SIDEBAR_TEXT}; padding: 3px 0; }}

    /* ---- Misc ---- */
    [data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden; }}

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
