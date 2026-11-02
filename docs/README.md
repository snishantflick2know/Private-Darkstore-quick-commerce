# Shelf Pulse frontend

Plain HTML, CSS and JavaScript (ES modules). No framework, no build step and no chart library: every chart is hand-drawn SVG in `js/charts.js`.

This is a faithful port of the Claude Design canvas "Shelf Pulse — Quick-Commerce Dashboard". The canvas uses Claude Design's own template format, which can't run outside Claude, so this code was rewritten from it 1:1. It has the same layout, wording, tokens and behaviour.

## Run it

ES modules don't load from `file://`, so serve the folder over HTTP:

```bash
cd shelf-pulse-frontend
python -m http.server 8000      # then open http://localhost:8000
```

Without a backend, the app shows the sample data in `js/data.js`.

Useful URL parameters:
- `?page=stock` opens a page directly. The other values are `competition`, `forecast` and `alerts`.
- `?store=3` opens the store panel for that store.
- `?notes=1` turns on the change-note markers.

## File map

| File | What it is |
|---|---|
| `index.html` | Loads the font, the two stylesheets and `js/app.js` |
| `css/tokens.css` | **Design tokens**: every colour, radius, font size and layout value, light and dark |
| `css/app.css` | Component styles, in the same order as the components |
| `js/data.js` | **Sample data = the API contract** (see below) |
| `js/app.js` | State, `fetch('/api/dashboard')`, render loop, one delegated click handler |
| `js/charts.js` | **All chart drawing**: `smoothPath`, `trendChart`, `sparkline`, `storeMap`, `horizontalBars`, `verticalBars`, `groupedBars` |
| `js/util.js` | `esc()` (escape every API string), `band()`, `badge()`, `duration()`, `clock()`, `units()` |
| `js/icons.js` | Line icons as inline SVG |
| `js/components/nav.js` | Left menu, brand switcher, "Data is up to date" card |
| `js/components/header.js` | Page header, platform switcher, filters, period |
| `js/components/overview.js` | Overview page: `heroCard` (headline + 7-day chart), `stockOnShelf`, `tiles`, `storeGrid`, `attention`, `outOfStockNow`, `storeHealth` |
| `js/components/stockouts.js` | Stock-outs page |
| `js/components/competition.js` | Competition page |
| `js/components/forecast.js` | "What runs out next" page |
| `js/components/alerts.js` | Alerts page with filters |
| `js/components/storePanel.js` | Store detail panel (opens from a grid row or map pin) |
| `server_example.py` | Minimal FastAPI app that serves this folder plus `/api/dashboard` |
| `reference/Main.dc.html` | Original canvas source, for reference only (doesn't run outside Claude) |

Every component is a pure function `(data, state) => htmlString`. Interactive elements carry `data-action="…"`, and `app.js` handles them all in one place.

## API contract

`GET /api/dashboard?platform=Blinkit&period=7D` → JSON shaped exactly like `SAMPLE` in `js/data.js`.

Rules the frontend relies on:
- **Raw values only.** Send `minutesOut: 230`, `since: "09:50"`, `availabilityPct: 86`. The components produce "3 hr 50 min", "9:50 am" and "86%".
- **Brand order matters.** `brands[0]` is always the logged-in brand. Arrays such as `trend.series[i]` and `stores[].values[i]` follow the same order as `brands`. Objects like `stockOnShelf[]` and `comparison[]` refer to a brand by its index in `brand`.
- **`colorVar`** must be one of `--brand`, `--c-real`, `--c-raw`, `--c-bn`, `--c-trop`. Add more tokens to `tokens.css` for more competitors.
- **Tones** are `crit`, `warn`, `ok`, `info`, `neutral` or `brand`.
- **Alert `type`** must be a key of `ALERT_TONE` in `js/components/alerts.js`.
- **`stores[].map`** gives positions on the 320 × 190 schematic map. Replace it with lat/lng and a real map (Leaflet) when ready.

How each number should be calculated is listed in the change notes, section 3 ("Numbers and how to calculate them"). Use those definitions in the backend.

## Wiring real data

Live data needs no frontend changes. `app.js` calls `loadData()` on start, on refresh, and when the platform or period changes. If the request fails, it falls back to the sample data. To serve both from FastAPI, see `server_example.py`.

## Design tokens

All design values are in `css/tokens.css`. Key ones:

- **Font:** DM Sans 400 to 700, one family, tabular numbers.
- **Type sizes:**
  - headline number 60 px
  - tile numbers 30 px
  - page title 22 px
  - card titles 15 px
  - body text 13 to 14 px
  - labels 12.5 px
- **Colours:**
  - brand: `#6E5BFF`
  - competitors: `#0D9488`, `#2563EB`, `#DB2777`, `#98A2B3`
  - status: critical `#D92D20` on `#FEF3F2`, watch `#DC6803` on `#FFFAEB`, healthy `#079455` on `#ECFDF3`
- **Layout:** cards have radius 16 px. Content padding is 22 × 28 px, max width 1480 px. Wide and narrow cards sit side by side at about 2 : 1.
- **Dark theme:** the `.dark` class on `<html>` switches it.
