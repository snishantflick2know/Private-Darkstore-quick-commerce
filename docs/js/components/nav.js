/* Left navigation (change note #1, #2, #3) */
import { esc } from '../util.js';
import { icon } from '../icons.js';

export const PAGES = [
  { id: 'overview',    label: 'Overview',           icon: 'overview' },
  { id: 'stock',       label: 'Stock-outs',         icon: 'stock',       count: d => d.stockouts.length, countTone: 'crit' },
  { id: 'competition', label: 'Competition',        icon: 'competition' },
  { id: 'forecast',    label: 'Depletion forecast', icon: 'forecast' },
  { id: 'alerts',      label: 'Alerts',             icon: 'alerts',      count: d => d.alerts.length, countTone: 'neutral' }
];

export function nav(data, state) {
  const { brand, meta } = data;
  const items = PAGES.map(p => `
    <button type="button" class="nav ${state.page === p.id ? 'on' : ''}" data-action="go" data-page="${p.id}">
      ${icon(p.icon)}${esc(p.label)}
      ${p.count ? `<span class="cnt b-${p.countTone}">${p.count(data)}</span>` : ''}
    </button>`).join('');

  // The original design also had a "Workspace" nav group (Alert rules, Data
  // sources) and a decorative, made-up "feed health" bar graph - both removed
  // since neither is backed by anything real yet.
  return `
  <aside class="rail" data-note="1">
    <div class="logo">
      <div class="logo-mark">${icon('logo')}</div>
      <div><div class="logo-name">Shelf Pulse</div><div class="logo-tag">Quick commerce</div></div>
    </div>

    <label class="brand-switch" data-note="2" style="position:relative;display:flex">
      <span class="avatar">${esc(brand.initials)}</span>
      <span style="flex:1;min-width:0"><span class="t1">${esc(brand.name)}</span><span class="t2">${esc(brand.company)}</span></span>
      ${icon('updown', 'sm')}
      <select data-action="brand" aria-label="Switch brand" style="position:absolute;inset:0;opacity:0;cursor:pointer">
        ${data.brands.map(b => `<option value="${esc(b.name)}" ${b.name === brand.name ? 'selected' : ''}>${esc(b.name)}</option>`).join('')}
      </select>
    </label>

    <nav class="nav-group" aria-label="Main">
      <div class="nav-label">Analytics</div>
      ${items}
    </nav>

    <div class="feed" data-note="3">
      <div class="feed-title"><span class="live-dot"></span>Data is up to date</div>
      <div class="feed-text">We check ${meta.storesChecked} ${esc(meta.platform)} stores every ${meta.checkIntervalMinutes} minutes. Next check in ${meta.nextCheckMinutes} min.</div>
    </div>
  </aside>`;
}
