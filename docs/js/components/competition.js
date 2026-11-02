/* Competition page (change note #17) */
import { esc, badge, duration, swatch } from '../util.js';
import { groupedBars } from '../charts.js';

export function competitionPage(data) {
  const you = data.comparison.find(r => r.brand === 0).availabilityPct;
  const legend = data.brands.map(b => `<span>${swatch(b.colorVar)}${esc(b.name)}</span>`).join('');

  const rows = data.comparison.map(r => {
    const b = data.brands[r.brand], own = r.brand === 0;
    const week = r.availabilityPct - r.previousPct;
    const vsYou = r.availabilityPct - you;
    return `
    <div class="trow cols-bench">
      <span style="display:flex;align-items:center;gap:8px;white-space:nowrap">${swatch(b.colorVar)}<span style="color:var(--ink);font-weight:${own ? 600 : 500}">${esc(b.name)}</span>${own ? badge('brand', 'You', false) : ''}</span>
      <span class="bar-cell"><span class="track"><span style="width:${r.availabilityPct}%;background:var(${b.colorVar})"></span></span><span class="num" style="width:36px;text-align:right;color:var(--ink)">${r.availabilityPct}%</span></span>
      <span class="r num ${week > 0 ? 'd-good' : week < 0 ? 'd-bad' : 'd-flat'}">${week > 0 ? '+' + week : week < 0 ? '−' + (-week) : 'same'}</span>
      <span class="r num ${own ? 'd-flat' : vsYou > 0 ? 'd-bad' : 'd-good'}">${own ? '' : vsYou > 0 ? `${vsYou} ahead` : `${-vsYou} behind`}</span>
      <span class="r num">${r.products}</span>
      <span class="r num">${r.outNow}</span>
    </div>`;
  }).join('');

  const theirs = data.competitorStockouts.map(c => `
    <div class="trow cols-comp-oos">
      <span><span class="cell-main">${esc(c.product)}</span><span class="cell-sub">${esc(c.pack)}, out for ${esc(c.outRange || duration(c.minutesOut))}</span></span>
      <span>${esc(c.store)}</span>
      <span>${c.yourOption ? badge('ok', c.yourOption) : badge('neutral', 'Nothing similar', false)}</span>
    </div>`).join('');

  return `
  <div class="stack" data-note="17">
    <section class="card pad">
      <div class="card-head">
        <div><h2 class="card-title">Availability by store and brand</h2><p class="card-sub">Each group is one dark store. The scale starts at 60%.</p></div>
        <div class="legend">${legend}</div>
      </div>
      ${groupedBars(data.stores, data.brands)}
    </section>
    <div class="row">
      <section class="card clip" style="flex:3 1 540px">
        <div class="card-head"><div><h2 class="card-title">How brands compare</h2><p class="card-sub">Every brand we track on ${esc(data.meta.platform)} in ${esc(data.meta.region)}</p></div><button type="button" class="btn" data-action="export">Download CSV</button></div>
        <div class="tscroll">
          <div class="thead cols-bench"><span>Brand</span><span>Availability</span><span class="r">Week</span><span class="r">vs you</span><span class="r">Items</span><span class="r">Out</span></div>
          ${rows}
        </div>
      </section>
      <section class="card clip" style="flex:2 1 360px">
        <div class="card-head"><div><h2 class="card-title">Where competitors ran out</h2><p class="card-sub">Good moments to push your own product</p></div></div>
        <div class="thead cols-comp-oos"><span>Their product</span><span>Store</span><span>Your option</span></div>
        ${theirs}
      </section>
    </div>
  </div>`;
}
