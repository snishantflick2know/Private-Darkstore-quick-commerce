/* "What runs out next" page (change note #18) */
import { esc, badge } from '../util.js';

// Thresholds: 6 hrs or less = reorder now, 12 hrs or less = reorder today
export function forecastTone(hoursLeft) {
  return hoursLeft <= 6 ? 'crit' : hoursLeft <= 12 ? 'warn' : 'neutral';
}
const ACTION = { crit: 'Reorder now', warn: 'Reorder today', neutral: 'On track' };
const BAR = { crit: '--crit', warn: '--warn', neutral: '--brand' };

export function forecastPage(data) {
  const rows = data.forecast.map(f => {
    const t = forecastTone(f.hoursLeft);
    return `
    <div class="trow cols-forecast">
      <span><span class="cell-main">${esc(f.product)}</span><span class="cell-sub">${esc(f.pack)}</span></span>
      <span>${esc(f.store)}</span>
      <span class="r num">${f.unitsLeft}</span>
      <span class="r num">${f.sellingPerHour} an hr</span>
      <span class="bar-cell"><span class="track"><span style="width:${Math.min(100, f.hoursLeft / 24 * 100).toFixed(1)}%;background:var(${BAR[t]})"></span></span><span class="num" style="width:60px;text-align:right;color:var(--ink)">${f.hoursLeft} hrs</span></span>
      <span>${badge(t, ACTION[t])}</span>
    </div>`;
  }).join('');
  return `
  <section class="card clip" data-note="18">
    <div class="card-head">
      <div><h2 class="card-title">What runs out next</h2><p class="card-sub">Based on how fast stock dropped over the last 6 hours</p></div>
      ${badge('warn', 'Rough estimate', false)}
    </div>
    <div class="tscroll">
      <div class="thead cols-forecast"><span>Product</span><span>Dark store</span><span class="r">Units left</span><span class="r">Selling</span><span>Time left</span><span>What to do</span></div>
      ${rows}
    </div>
  </section>`;
}
