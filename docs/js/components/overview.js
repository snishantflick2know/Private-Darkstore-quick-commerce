/* Overview page (change notes #7 to #14) */
import { esc, band, BAND_LABEL, badge, duration, units, swatch } from '../util.js';
import { trendChart, sparkline, storeMap } from '../charts.js';
import { icon } from '../icons.js';

const ORDINAL = n => n + (['th', 'st', 'nd', 'rd'][(n % 100 - 20) % 10] || ['th', 'st', 'nd', 'rd'][n % 100] || 'th');

/* #7 + #8 — headline availability and 7-day trend */
export function heroCard(data) {
  const h = data.headline;
  const diff = h.availabilityPct - h.previousPct;
  const direction = diff < 0 ? `Down ${-diff} points` : diff > 0 ? `Up ${diff} points` : 'No change';
  const legend = data.brands.map(b => `<span>${swatch(b.colorVar)}${esc(b.name)}</span>`).join('');
  const avgH = Math.floor(h.averageOutageMinutes / 60), avgM = h.averageOutageMinutes % 60;
  return `
  <section class="card col-wide hero" data-note="7">
    <div class="hero-left">
      <div class="hero-kicker">On-shelf availability</div>
      <div class="hero-value num">${h.availabilityPct}<small>%</small></div>
      <p class="hero-summary"><b>${direction}</b> from ${h.previousPct}% last week. You're ${ORDINAL(h.rank)} of ${data.brands.length} brands.</p>
      <div class="hero-stats">
        <div><div class="stat-label">Products in stock</div><div class="stat-value num">${h.productsInStock} <small>of ${data.brand.totalProducts}</small></div></div>
        <div><div class="stat-label">Behind ${esc(h.leaderName)}</div><div class="stat-value num d-bad">${h.pointsBehindLeader} points</div></div>
        <div><div class="stat-label">Hours off shelf</div><div class="stat-value num">${h.hoursOffShelf} hrs <small class="d-bad">${h.peakHoursOffShelf != null ? `${h.peakHoursOffShelf} in peak` : `up ${h.hoursOffShelfChange}`}</small></div></div>
        <div><div class="stat-label">Average outage</div><div class="stat-value num">${avgH} hr ${avgM} min</div></div>
      </div>
    </div>
    <div class="hero-right" data-note="8">
      <div class="hero-right-head"><span class="hero-kicker">Availability over the last ${data.trend.days.length} days</span><div class="legend">${legend}</div></div>
      ${trendChart({ days: data.trend.days, series: data.trend.series, brands: data.brands })}
    </div>
  </section>`;
}

/* #9 — stock on shelf in the region */
export function stockOnShelf(data) {
  const total = data.stockOnShelf.reduce((t, r) => t + r.units, 0);
  const seg = data.stockOnShelf.map(r =>
    `<span style="width:${(r.units / total * 100).toFixed(1)}%;background:var(${data.brands[r.brand].colorVar})"></span>`).join('');
  const rows = data.stockOnShelf.map(r => {
    const b = data.brands[r.brand], own = r.brand === 0;
    return `
    <div class="inv-grid inv-row ${own ? 'own' : ''}">
      ${swatch(b.colorVar)}
      <span class="name">${esc(b.name)}${own ? ' (you)' : ''}</span>
      <span class="r num">${units(r.units)}</span>
      <span class="r num">${Math.round(r.units / total * 100)}%</span>
      <span class="r num ${r.changePct < 0 ? 'd-bad' : 'd-good'}">${r.changePct < 0 ? '−' : '+'}${Math.abs(r.changePct)}%</span>
    </div>`;
  }).join('');
  return `
  <section class="card pad col-narrow" data-note="9" style="display:flex;flex-direction:column">
    <h2 class="card-title">Stock on shelf in ${esc(data.meta.region)}</h2>
    <p class="card-sub">Units across ${data.stores.length} dark stores at the last check</p>
    <div class="inv-total"><b class="num">${units(total)}</b><span>${esc(data.meta.category.toLowerCase())} units in total</span></div>
    <div class="share-bar">${seg}</div>
    <div class="inv-grid inv-head"><span></span><span>Brand</span><span class="r">Units</span><span class="r">Share</span><span class="r">Week</span></div>
    ${rows}
  </section>`;
}

/* #10 — four tiles */
export function tiles(data) {
  const TONE_VAR = { crit: '--crit', warn: '--warn', ok: '--ok', brand: '--brand' };
  return `
  <section class="tiles" aria-label="Key numbers" data-note="10">${data.tiles.map(t => `
    <div class="card tile">
      <div class="tile-label">${esc(t.label)}</div>
      <div class="tile-row">
        <div class="tile-value num">${t.value}<small>${esc(t.unit)}</small></div>
        ${sparkline(t.trend, TONE_VAR[t.tone])}
      </div>
      <div class="tile-foot">${t.delta ? `<span class="${t.deltaTone === 'bad' ? 'd-bad' : 'd-good'}">${esc(t.delta)}</span>` : ''}${esc(t.note)}</div>
    </div>`).join('')}
  </section>`;
}

/* #11 — store × brand grid; rows open the store panel */
export function storeGrid(data) {
  const head = data.brands.map((b, i) => `<span class="c ${i === 0 ? 'own' : ''}">${esc(b.name)}</span>`).join('');
  const rows = data.stores.map((s, si) => {
    const out = data.stockouts.filter(o => o.store === s.name).length;
    const tone = band(s.values[0]);
    return `
    <button type="button" class="hm-row" data-action="open-store" data-store="${si}" aria-label="Open ${esc(s.name)}">
      <span class="hm-grid">
        <span><span class="store-name">${esc(s.name)}</span><span class="store-meta">${esc(s.city)}, ${out ? `${out} out of stock` : 'nothing missing'}</span></span>
        ${s.values.map((v, i) => `<span class="cell h-${band(v)} ${i === 0 ? 'own' : ''}">${v}%</span>`).join('')}
        <span style="padding-left:6px">${badge(tone, BAND_LABEL[tone])}</span>
      </span>
    </button>`;
  }).join('');
  const avg = data.brands.map((b, i) => {
    const a = Math.round(data.stores.reduce((t, s) => t + s.values[i], 0) / data.stores.length);
    return `<span class="cell h-avg ${i === 0 ? 'own' : ''}">${a}%</span>`;
  }).join('');
  return `
  <section class="card col-wide" data-note="11">
    <div class="card-head">
      <div><h2 class="card-title">Availability by dark store</h2><p class="card-sub">Click a store to see what's missing there. Your brand is outlined.</p></div>
      <div class="legend"><span><span class="sw" style="background:var(--ok)"></span>90% or more</span><span><span class="sw" style="background:var(--warn)"></span>80–89%</span><span><span class="sw" style="background:var(--crit)"></span>Under 80%</span></div>
    </div>
    <div class="hm-wrap"><div class="hm">
      <div class="hm-grid hm-head"><span>Dark store</span>${head}<span style="padding-left:6px">Status</span></div>
      ${rows}
      <div class="hm-grid"><span><span class="store-name">Average</span><span class="store-meta">All ${data.stores.length} stores</span></span>${avg}<span></span></div>
    </div></div>
  </section>`;
}

/* #12 — needs your attention */
export function attention(data) {
  return `
  <section class="card col-narrow" data-note="12" style="display:flex;flex-direction:column">
    <div class="card-head">
      <div><h2 class="card-title">Needs your attention</h2><p class="card-sub">Most urgent first</p></div>
      ${badge('crit', `${data.attention.length} to do`, false)}
    </div>
    ${data.attention.map(a => `
    <div class="att-item">
      <span class="att-icon ${a.tone}">${icon('attention', 'sm')}</span>
      <div><div class="att-title">${esc(a.title)}</div><div class="att-meta">${esc(a.detail)}</div></div>
      <button type="button" class="btn small" data-action="go" data-page="${a.goTo}">${esc(a.action)}</button>
    </div>`).join('')}
  </section>`;
}

/* #13 — out of stock right now (compact) */
export function outOfStockNow(data) {
  const rows = [...data.stockouts].sort((a, b) => b.minutesOut - a.minutesOut).map(o => `
    <div class="trow cols-oos-mini">
      <span><span class="cell-main">${esc(o.product)}</span><span class="cell-sub">${esc(o.pack)}, ₹${o.mrp}</span></span>
      <span>${esc(o.store)}</span>
      <span class="r num" style="color:var(--ink)">${esc(o.outRange || duration(o.minutesOut))}</span>
      <span>${badge(o.nearby.tone, o.nearby.text)}</span>
    </div>`).join('');
  return `
  <section class="card clip col-wide" data-note="13">
    <div class="card-head">
      <div><h2 class="card-title">Out of stock right now</h2><p class="card-sub">Your products, longest outage first, and whether a nearby store has them. Durations are honest ranges between checks, not point guesses.</p></div>
      <button type="button" class="link" data-action="go" data-page="stock">View all →</button>
    </div>
    <div class="tscroll">
      <div class="thead cols-oos-mini"><span>Product</span><span>Dark store</span><span class="r">Out for</span><span>Nearby stores</span></div>
      ${rows}
    </div>
  </section>`;
}

/* #14 — store health map + sorted list */
export function storeHealth(data) {
  const list = data.stores.map((s, i) => ({ s, i })).sort((a, b) => a.s.values[0] - b.s.values[0]).map(({ s }) => {
    const t = band(s.values[0]);
    return `<div class="store-li"><span>${esc(s.name)} <span style="color:var(--subtle)">${esc(s.city)}</span></span><span style="display:flex;gap:10px;align-items:center"><span class="num">${s.values[0]}%</span>${badge(t, BAND_LABEL[t])}</span></div>`;
  }).join('');
  return `
  <section class="card pad col-narrow" data-note="14">
    <h2 class="card-title">Store health</h2>
    <p class="card-sub">How your brand is doing at each store</p>
    <div class="map-box">${storeMap(data.stores)}<span class="map-note">Not to scale</span></div>
    <div style="margin-top:10px">${list}</div>
  </section>`;
}

export function overviewPage(data) {
  return `
  <div class="stack">
    <div class="row">${heroCard(data)}${stockOnShelf(data)}</div>
    ${tiles(data)}
    <div class="row">${storeGrid(data)}${attention(data)}</div>
    <div class="row">${outOfStockNow(data)}${storeHealth(data)}</div>
  </div>`;
}
