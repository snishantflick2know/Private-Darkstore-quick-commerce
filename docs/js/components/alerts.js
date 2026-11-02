/* Alerts page (change note #19) */
import { esc, badge, clock } from '../util.js';

export const ALERT_TONE = {
  'Out of stock': 'crit', 'Delisted': 'crit',
  'Running low': 'warn', 'Competitor gap': 'warn',
  'New product': 'info', 'Back in stock': 'ok'
};
const TYPES = ['All', ...Object.keys(ALERT_TONE)];

export function alertsPage(data, state) {
  const chips = TYPES.map(t => {
    const n = t === 'All' ? data.alerts.length : data.alerts.filter(a => a.type === t).length;
    return `<button type="button" class="chip ${state.alertType === t ? 'on' : ''}" data-action="alert-filter" data-value="${esc(t)}">${esc(t)} (${n})</button>`;
  }).join('');
  const rows = data.alerts.filter(a => state.alertType === 'All' || a.type === state.alertType).map(a => `
    <div class="alert-row">
      <span class="alert-time">${clock(a.time)}</span>
      <span>${badge(ALERT_TONE[a.type] || 'neutral', a.type)}</span>
      <span>${esc(a.text)}</span>
    </div>`).join('');
  return `
  <section class="card clip" data-note="19">
    <div class="card-head">
      <div><h2 class="card-title">Today's alerts</h2><p class="card-sub">Everything we flagged today, from comparing each live check against the one before it.</p></div>
      <button type="button" class="btn" data-action="export">Download CSV</button>
    </div>
    <div class="chips" role="group" aria-label="Filter alerts">${chips}</div>
    ${rows}
  </section>`;
}
