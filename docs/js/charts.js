/* =====================================================================
   Chart drawing — plain SVG strings, no chart library.
   Every function returns an HTML/SVG string to drop into a template.
   Colours are CSS variables, so charts follow the light/dark theme.
   ===================================================================== */

import { esc, band } from './util.js';

/**
 * Smooth line through points using Catmull-Rom → cubic Bézier.
 * points: [[x, y], ...]  →  SVG path "M x y C ..."
 * This is what gives the trend chart and sparklines their soft curves.
 */
export function smoothPath(points) {
  let d = `M${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

/**
 * 7-day availability trend: your brand as a thick line with a soft fill,
 * competitors as thin lines. Fixed 75–100% scale.
 * days: ['27 Oct', ...]; series: [[...], ...] in brand order; brands: [{colorVar}]
 */
export function trendChart({ days, series, brands, min = 75, max = 100 }) {
  const W = 640, H = 270, L = 48, R = 628, T = 12, B = 236;
  const n = days.length;
  const X = i => L + i * (R - L) / (n - 1);
  const Y = v => T + (max - v) / (max - min) * (B - T);

  const ticks = [];
  for (let v = max; v >= min; v -= 5) ticks.push(v);
  const grid = ticks.map(v => `
    <line x1="${L}" x2="${R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" class="gl"></line>
    <text x="40" y="${(Y(v) + 5).toFixed(1)}" class="axis" text-anchor="end">${v}%</text>`).join('');
  const xLabels = days.map((d, i) => `<text x="${X(i).toFixed(1)}" y="262" class="axis" text-anchor="middle">${esc(d)}</text>`).join('');

  const ownPts = series[0].map((v, i) => [X(i), Y(v)]);
  const ownLine = smoothPath(ownPts);
  const ownArea = `${ownLine} L${R} ${B} L${L} ${B} Z`;
  const competitors = series.slice(1).map((vals, k) =>
    `<path d="${smoothPath(vals.map((v, i) => [X(i), Y(v)]))}" class="ln" style="stroke:var(${brands[k + 1].colorVar})"></path>`).join('');
  const [lx, ly] = ownPts[n - 1];

  return `
  <svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="Availability over the last ${n} days, your brand against competitors">
    <defs>
      <linearGradient id="ownArea" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" style="stop-color:var(--brand);stop-opacity:.26"></stop>
        <stop offset="1" style="stop-color:var(--brand);stop-opacity:0"></stop>
      </linearGradient>
    </defs>
    ${grid}${xLabels}
    <path d="${ownArea}" fill="url(#ownArea)"></path>
    ${competitors}
    <path d="${ownLine}" class="ln-own"></path>
    <circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="5" style="fill:var(--surface);stroke:var(--brand);stroke-width:2.5"></circle>
  </svg>`;
}

/**
 * Tile sparkline (96 x 36). Scales to the series' own min/max.
 * colorVar: e.g. '--crit'
 */
export function sparkline(values, colorVar) {
  const mn = Math.min(...values), mx = Math.max(...values), range = (mx - mn) || 1;
  const pts = values.map((v, i) => [3 + i * 90 / (values.length - 1), 31 - (v - mn) / range * 26]);
  const line = smoothPath(pts);
  return `
  <svg viewBox="0 0 96 36" class="spark" aria-hidden="true">
    <path d="${line} L93 36 L3 36 Z" style="fill:var(${colorVar});opacity:.1"></path>
    <path d="${line}" style="fill:none;stroke:var(${colorVar});stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round"></path>
  </svg>`;
}

/**
 * Store health map: schematic roads + one pin per store, coloured by
 * YOUR availability at that store. Pins carry data-action="open-store".
 * Swap for Leaflet/Mapbox with real lat/lng in production.
 */
export function storeMap(stores) {
  const PIN = { ok: '--ok', warn: '--warn', crit: '--crit' };
  const pins = stores.map((s, i) => {
    const c = PIN[band(s.values[0])];
    return `
    <g class="pin" data-action="open-store" data-store="${i}" role="button" tabindex="0" aria-label="Open ${esc(s.name)}">
      <circle cx="${s.map.x}" cy="${s.map.y}" r="15" style="fill:var(${c});opacity:.16"></circle>
      <circle cx="${s.map.x}" cy="${s.map.y}" r="6" style="fill:var(${c});stroke:var(--map-bg);stroke-width:2.5"></circle>
      <text x="${s.map.lx}" y="${s.map.ly}" text-anchor="${s.map.anchor}" class="pin-label">${esc(s.name)}</text>
    </g>`;
  }).join('');
  return `
  <svg viewBox="0 0 320 190" class="chart" role="img" aria-label="Map of ${stores.length} dark stores">
    <path d="M0 58 C80 48 140 88 320 68" style="fill:none;stroke:var(--map-road);stroke-width:7;stroke-linecap:round"></path>
    <path d="M150 0 C140 66 120 130 92 190" style="fill:none;stroke:var(--map-road);stroke-width:7;stroke-linecap:round"></path>
    <path d="M30 116 C120 124 220 134 320 144" style="fill:none;stroke:var(--map-road);stroke-width:5;stroke-linecap:round"></path>
    <path d="M210 0 C220 58 236 124 262 190" style="fill:none;stroke:var(--map-river);stroke-width:10;stroke-linecap:round"></path>
    ${pins}
  </svg>`;
}

/** Horizontal bars (hours off shelf). Scale max defaults to the largest value rounded up. */
export function horizontalBars(rows, { max } = {}) {
  const top = max ?? Math.ceil(Math.max(...rows.map(r => r.value)));
  return `<div class="hbars">${rows.map(r => `
    <div class="hbar">
      <span>${esc(r.label)}</span>
      <span class="bg"><span style="width:${(r.value / top * 100).toFixed(1)}%"></span></span>
      <span class="num" style="text-align:right">${esc(r.display)}</span>
    </div>`).join('')}</div>`;
}

/** Vertical bars (stock-outs by store). Tallest bar = 82% of the plot height. */
export function verticalBars(rows) {
  const top = Math.max(...rows.map(r => r.value)) || 1;
  return `
  <div class="vbars">${rows.map(r => `
    <div class="vbar"><span class="num">${r.value}</span><span class="bar" style="height:${(r.value / top * 82).toFixed(1)}%"></span></div>`).join('')}
  </div>
  <div class="vbar-labels">${rows.map(r => `<span>${esc(r.label)}</span>`).join('')}</div>`;
}

/**
 * Grouped bars: one group per store, one bar per brand.
 * Axis starts at `floor` (60%) so differences are visible.
 */
export function groupedBars(stores, brands, { floor = 60, ceil = 100 } = {}) {
  const groups = stores.map(s => `
    <div class="group">${s.values.map((v, i) =>
      `<span title="${esc(brands[i].name)} ${v}%" style="background:var(${brands[i].colorVar});height:${((v - floor) / (ceil - floor) * 100).toFixed(1)}%"></span>`).join('')}
    </div>`).join('');
  return `
  <div class="tscroll"><div style="min-width:640px">
    <div class="groups">${groups}</div>
    <div class="group-labels">${stores.map(s => `<span>${esc(s.name)}</span>`).join('')}</div>
  </div></div>`;
}
