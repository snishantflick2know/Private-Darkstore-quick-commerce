/* Full product catalog - every tracked brand's products, with live
   inventory per store. This existed in the Streamlit app's drill-down
   tables (brand's SKUs, availability-by-brand breakdown) but had no
   equivalent in the redesigned pages, so it's added here rather than lost.
   Not part of the original canvas/data.js contract - see data.products. */
import { esc, badge } from '../util.js';

export function productCatalog(data, state) {
  const brandFilter = state.productBrand || 'All';
  const storeFilter = state.productStore || 'All';
  const view = state.productView || 'latest';  // 'latest' = one row per product/store (deduped), 'history' = every scrape run

  const brandChips = ['All', ...data.brands.map(b => b.name)].map(name => `
    <button type="button" class="chip ${brandFilter === name ? 'on' : ''}" data-action="product-filter" data-value="${esc(name)}">${esc(name)}</button>`).join('');
  const storeChips = ['All', ...data.stores.map(s => s.name)].map(name => `
    <button type="button" class="chip ${storeFilter === name ? 'on' : ''}" data-action="product-store-filter" data-value="${esc(name)}">${esc(name)}</button>`).join('');

  const source = view === 'history' ? (data.snapshotHistory || []) : (data.products || []);
  const products = source
    .filter(p => brandFilter === 'All' || p.brand === brandFilter)
    .filter(p => storeFilter === 'All' || p.store === storeFilter);
  // History can be thousands of rows - cap what the DOM renders (newest first,
  // already sorted that way by the backend) and say so rather than hanging the page.
  const MAX_ROWS = 500;
  const shown = products.slice(0, MAX_ROWS);
  const rows = shown.map(p => `
    <div class="trow cols-products">
      <span style="font-weight:500">${esc(p.brand)}</span>
      <span><span class="cell-main">${esc(p.product)}</span><span class="cell-sub">${esc(p.pack)}</span></span>
      <span>${esc(p.store)}</span>
      <span class="num" style="color:var(--subtle)">${esc(p.merchantId || '—')}</span>
      <span class="r num">₹${p.price}</span>
      <span class="r num" style="color:var(--subtle)">₹${p.mrp}</span>
      <span class="r num">${p.inventory}</span>
      <span>${p.status === 'Out of stock' ? badge('crit', 'Out of stock') : badge('ok', 'In stock')}</span>
      <span class="num" style="color:var(--subtle);white-space:nowrap">${esc(p.capturedAt)}</span>
    </div>`).join('');

  const sub = view === 'history'
    ? `Every scrape run, newest first - the same product repeats once per check, so you can watch its stock change hour over hour (the append-only <code>snapshots</code> table, unmodified).`
    : `Every tracked brand's products and live inventory, at the last check - deduplicated to the newest row per product per store.`;

  return `
  <section class="card clip">
    <div class="card-head">
      <div><h2 class="card-title">All products</h2><p class="card-sub">${sub}</p></div>
      <div style="display:flex;gap:8px;align-items:center">
        <div class="chips" role="group" aria-label="Rows shown">
          <button type="button" class="chip ${view === 'latest' ? 'on' : ''}" data-action="product-view" data-value="latest">Latest only</button>
          <button type="button" class="chip ${view === 'history' ? 'on' : ''}" data-action="product-view" data-value="history">Full history</button>
        </div>
        <button type="button" class="btn" data-action="export">Download CSV</button>
      </div>
    </div>
    <div class="chips" role="group" aria-label="Filter by brand" style="margin-bottom:8px">${brandChips}</div>
    <div class="chips" role="group" aria-label="Filter by store">${storeChips}</div>
    <div class="tscroll">
      <div class="thead cols-products"><span>Brand</span><span>Product</span><span>Store</span><span>Merchant ID</span><span class="r">Price</span><span class="r">MRP</span><span class="r">Inventory</span><span>Status</span><span>Captured at</span></div>
      ${rows || '<div class="panel-empty" style="padding:20px">No products found for this filter.</div>'}
      ${products.length > MAX_ROWS ? `<div class="panel-empty" style="padding:12px">Showing the newest ${MAX_ROWS} of ${products.length} rows - narrow the brand/store filters to see more.</div>` : ''}
    </div>
  </section>`;
}
