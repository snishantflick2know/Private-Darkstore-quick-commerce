/* Stock-outs page (change note #16) */
import { esc, badge, duration } from '../util.js';
import { horizontalBars, verticalBars } from '../charts.js';

const times = n => n === 1 ? 'Once' : `${n} times`;

export function stockoutsPage(data) {
  // Keep each row's real index into data.stockouts (for the check-nearby
  // action) even after sorting by minutesOut.
  const indexed = data.stockouts.map((o, i) => ({ o, i })).sort((a, b) => b.o.minutesOut - a.o.minutesOut);
  const rows = indexed.map(({ o, i }) => `
    <div class="trow cols-oos-full">
      <span><span class="cell-main">${esc(o.product)}</span><span class="cell-sub">${esc(o.pack)}, ₹${o.mrp}</span></span>
      <span>${esc(o.store)}</span>
      <span class="num" style="white-space:nowrap">${esc(o.outBetween || (o.since ? 'since ' + o.since : '—'))}${o.outDuringPeak ? ' ' + badge('warn', 'peak hrs') : ''}</span>
      <span class="r num" style="color:var(--ink)">${esc(o.outRange || duration(o.minutesOut))}</span>
      <span class="r">${times(o.timesThisWeek)}</span>
      <span>${o.nearby.tone === 'neutral' && o.nearby.text === 'Check nearby stores'
        ? `<button type="button" class="btn small" data-action="check-nearby" data-index="${i}">Check nearby stores</button>`
        : badge(o.nearby.tone, o.nearby.text)}</span>
      <span>${o.competitorInStock ? badge('warn', esc(o.competitorInStock)) : 'None'}</span>
    </div>`).join('');

  const hours = horizontalBars(
    data.hoursOffShelf.map(r => ({ label: r.product, value: r.hours, display: `${r.hours} hrs` })), { max: 12 });
  const byStore = verticalBars(data.stockoutsByStore.map(r => ({ label: r.store, value: r.count })));

  return `
  <div class="stack" data-note="16">
    <section class="card clip">
      <div class="card-head">
        <div><h2 class="card-title">Your products that are out of stock</h2><p class="card-sub">"Went out" is an honest window, not a guess - we only see stock at each check, so it's the gap between the last in-stock and first out-of-stock reading (it tightens as checks get more frequent). "Competitor in stock" = rival brands still selling at that store right now - those are lost sales.</p></div>
        <div style="display:flex;gap:8px"><button type="button" class="btn" data-action="export">Download CSV</button></div>
      </div>
      <div class="tscroll">
        <div class="thead cols-oos-full"><span>Product</span><span>Dark store</span><span>Went out</span><span class="r">Out for</span><span class="r">This week</span><span>Nearby stores</span><span>Competitor in stock</span></div>
        ${rows}
      </div>
    </section>
    <div class="row">
      <section class="card pad" style="flex:3 1 480px">
        <h2 class="card-title">Hours off the shelf</h2>
        <p class="card-sub" style="margin-bottom:16px">Products that ran out at least once in the last 7 days</p>
        ${hours}
      </section>
      <section class="card pad" style="flex:2 1 360px">
        <h2 class="card-title">Stock-outs by store</h2>
        <p class="card-sub" style="margin-bottom:16px">How many times your products ran out this week</p>
        ${byStore}
      </section>
    </div>
  </div>`;
}
