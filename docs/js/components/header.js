/* Page header + filter bar (change notes #4, #5, #6) */
import { esc } from '../util.js';
import { icon } from '../icons.js';

export const PAGE_TITLES = {
  overview:    ['Overview',    'How your shelf looks today'],
  stock:       ['Stock-outs',  "What's out of stock"],
  competition: ['Competition', 'You vs other brands'],
  forecast:    ['Forecast',    'What runs out next'],
  alerts:      ['Alerts',      'Alerts']
};

// Zepto/Instamart and the Today/7D/30D period toggle were in the original
// design but aren't backed by real data (only Blinkit is scraped; the
// backend doesn't do period-windowed queries yet) - removed rather than
// shown-but-disabled, since the ask was to not show controls for things that
// don't exist yet. Same for the search box and "Show changes" button (a
// design-review tool, not a product feature) and the Region/Dark
// stores/Competitors/Category "chips", which looked like dropdowns (chevron
// icon) but had no action behind them - they're now plain, non-clickable info.

export function header(data, state) {
  const [crumb, title] = PAGE_TITLES[state.page];
  return `
  <header class="header" data-note="4">
    <div style="min-width:0">
      <div class="crumb">${esc(data.brand.name)} › ${esc(crumb)}</div>
      <h1 class="page-title">${esc(title)}</h1>
    </div>
    <div class="header-actions">
      <button type="button" class="btn icon" data-action="toggle-theme" aria-label="Switch light or dark theme">${icon(state.theme === 'dark' ? 'sun' : 'moon', 'sm')}</button>
      <button type="button" class="btn icon ${state.busy ? 'notes-on' : ''}" data-action="refresh" aria-label="Refresh" ${state.busy ? 'disabled' : ''}>${icon('refresh', 'sm')}</button>
      <button type="button" class="btn primary" data-action="export">${icon('download', 'sm')}Export</button>
    </div>
  </header>`;
}

export function filters(data) {
  const info = (label, value) => `<span class="fchip" style="cursor:default">${label} <b>${esc(value)}</b></span>`;
  return `
  <div class="filters">
    <span class="fchip" style="cursor:default;font-weight:600">${esc(data.meta.platform)}</span>
    ${info('Region', data.meta.region)}
    ${info('Dark stores', `All ${data.stores.length}`)}
    ${info('Competitors', `${data.brands.length - 1} brands`)}
    ${info('Category', data.meta.category)}
    <span class="updated"><span class="live-dot"></span>Updated ${data.meta.updatedMinutesAgo} min ago</span>
  </div>`;
}
