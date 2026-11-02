/* Store detail panel (change note #15). Opens from a store-grid row or a map pin. */
import { esc, band, BAND_LABEL, badge, duration } from '../util.js';
import { icon } from '../icons.js';

export function storePanel(data, storeIndex) {
  if (storeIndex == null || storeIndex < 0) return '';
  const s = data.stores[storeIndex];
  const tone = band(s.values[0]);
  const rank = [...s.values].sort((a, b) => b - a).indexOf(s.values[0]) + 1;
  const outHere = data.stockouts.filter(o => o.store === s.name);

  const bars = s.values.map((v, i) => ({ v, b: data.brands[i], own: i === 0 }))
    .sort((a, b) => b.v - a.v)
    .map(x => `
      <div class="panel-bar">
        <span style="${x.own ? 'font-weight:600' : 'color:var(--ink-2)'}">${esc(x.b.name)}</span>
        <span class="track"><span style="width:${x.v}%;background:var(${x.b.colorVar})"></span></span>
        <span class="num" style="text-align:right">${x.v}%</span>
      </div>`).join('');

  const missing = outHere.length
    ? outHere.map(o => `
      <div class="panel-oos">
        <span><span class="cell-main">${esc(o.product)} ${esc(o.pack)}</span><span class="cell-sub">Out for ${esc(o.outRange || duration(o.minutesOut))}</span></span>
        ${badge(o.nearby.tone, o.nearby.text)}
      </div>`).join('')
    : `<div class="panel-empty">No stock-outs for your brand at this store right now.</div>`;

  return `
  <div class="panel-overlay">
    <button type="button" class="panel-scrim" data-action="close-store" aria-label="Close store panel"></button>
    <aside class="panel" aria-label="Store details" data-note="15">
      <div class="panel-head">
        <div>
          <div class="panel-kicker">Dark store in ${esc(s.city)}</div>
          <h2 class="panel-title">${esc(s.name)}</h2>
          ${badge(tone, BAND_LABEL[tone])}
        </div>
        <button type="button" class="btn icon" data-action="close-store" aria-label="Close">${icon('close', 'sm')}</button>
      </div>
      <div class="panel-stats">
        <div><div class="stat-label">Your availability</div><div class="v num">${s.values[0]}%</div></div>
        <div><div class="stat-label">Out of stock</div><div class="v num">${outHere.length}</div></div>
        <div><div class="stat-label">Your rank here</div><div class="v num">${rank} of ${s.values.length}</div></div>
      </div>
      <div class="panel-section"><div class="stat-label">Availability at this store</div>${bars}</div>
      <div class="panel-section" style="gap:4px;border-bottom:0"><div class="stat-label" style="margin-bottom:6px">Your products out of stock here</div>${missing}</div>
    </aside>
  </div>`;
}
