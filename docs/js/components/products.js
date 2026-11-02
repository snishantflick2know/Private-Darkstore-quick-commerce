/* Full product catalog - every tracked brand's products, with live
   inventory per store. This existed in the Streamlit app's drill-down
   tables (brand's SKUs, availability-by-brand breakdown) but had no
   equivalent in the redesigned pages, so it's added here rather than lost.
   Not part of the original canvas/data.js contract - see data.products. */
import { esc, badge } from '../util.js';

export function productCatalog(data, state) {
  const brandFilter = state.productBrand || 'All';
  const storeFilter = state.productStore || 'All';

  const brandChips = ['All', ...data.brands.map(b => b.name)].map(name => `
    <button type="button" class="chip ${brandFilter === name ? 'on' : ''}" data-action="product-filter" data-value="${esc(name)}">${esc(name)}</button>`).join('');
  const storeChips = ['All', ...data.stores.map(s => s.name)].map(name => `
    <button type="button" class="chip ${storeFilter === name ? 'on' : ''}" data-action="product-store-filter" data-value="${esc(name)}">${esc(name)}</button>`).join('');

  const products = (data.products || [])
    .filter(p => brandFilter === 'All' || p.brand === brandFilter)
    .filter(p => storeFilter === 'All' || p.store === storeFilter);
  const rows = products.map(p => `
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

  return `
  <section class="card clip">
    <div class="card-head">
      <div><h2 class="card-title">All products</h2><p class="card-sub">Every tracked brand's products and live inventory, at the last check - the raw <code>snapshots</code> data, not a summary</p></div>
      <button type="button" class="btn" data-action="export">Download CSV</button>
    </div>
    <div class="chips" role="group" aria-label="Filter by brand" style="margin-bottom:8px">${brandChips}</div>
    <div class="chips" role="group" aria-label="Filter by store">${storeChips}</div>
    <div class="tscroll">
      <div class="thead cols-products"><span>Brand</span><span>Product</span><span>Store</span><span>Merchant ID</span><span class="r">Price</span><span class="r">MRP</span><span class="r">Inventory</span><span>Status</span><span>Captured at</span></div>
      ${rows || '<div class="panel-empty" style="padding:20px">No products found for this filter.</div>'}
    </div>
  </section>`;
}
