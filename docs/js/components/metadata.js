/* Metadata page - the raw underlying data behind every number on the
   dashboard (every tracked brand's products, with live inventory per
   store, pulled straight from the `snapshots` SQLite table), plus an
   explanation of what each column actually means. Not part of the
   original canvas/data.js contract - see data.products and products.js. */
import { icon } from '../icons.js';
import { productCatalog } from './products.js';

// Mirrors storage/db.py's SCHEMA exactly - keep this in sync if that changes.
const SNAPSHOT_SCHEMA = [
  ['id', 'INTEGER (PK, autoincrement)', 'Row ID', '10666'],
  ['platform', 'TEXT', 'Source platform', 'blinkit'],
  ['location_name', 'TEXT', 'Configured area name', 'Lajpat Nagar'],
  ['pincode', 'TEXT', 'Area pincode (informational)', '110024'],
  ['merchant_id', 'TEXT', "Blinkit's internal dark-store ID actually serving this check", '35554'],
  ['query', 'TEXT', 'Search term that surfaced this product', 'raw pressery'],
  ['product_id', 'TEXT', "Blinkit's internal product ID", '776334'],
  ['brand', 'TEXT', "Product's brand (normalized - see BRAND_ALIASES)", 'Pluckk'],
  ['name', 'TEXT', 'Product display name', 'Pluckk Cold Pressed Aam Panna Juice'],
  ['unit', 'TEXT', 'Pack size', '250 ml'],
  ['price', 'REAL', 'Selling price (₹)', '106.0'],
  ['mrp', 'REAL', 'MRP (₹)', '109.0'],
  ['inventory', 'INTEGER', 'Units reported in stock', '1'],
  ['is_sold_out', 'INTEGER (0/1)', 'Authoritative sold-out flag from Blinkit', '0'],
  ['fetched_at', 'TEXT (ISO-8601, UTC)', 'Exact timestamp this row was captured', '2026-11-02T09:18:59+00:00'],
  ['is_synthetic', 'INTEGER (0/1)', '1 = seeded/demo data, 0 = real live scrape', '0'],
];

function schemaRow([col, type, meaning, example]) {
  return `<tr><td><code>${col}</code></td><td><code>${type}</code></td><td>${meaning}</td><td><code>${example}</code></td></tr>`;
}

function schemaInfo() {
  return `
  <details class="meta-info">
    <summary>${icon('info', 'sm')} What do these columns mean?</summary>
    <div class="meta-info-body">
      <h3>Table 1: <code>snapshots</code> — one row per product, per store, per scrape</h3>
      <table class="meta-table">
        <thead><tr><th>Column</th><th>Type</th><th>Meaning</th><th>Example</th></tr></thead>
        <tbody>${SNAPSHOT_SCHEMA.map(schemaRow).join('')}</tbody>
      </table>
      <p style="font-size:12.5px;color:var(--subtle);margin-top:12px">
        No row is ever updated or deleted on each scrape - every check just appends new rows, which is what the
        trend and depletion-forecast charts read their history from. Rows older than 30 days are automatically
        pruned (see <code>storage/db.py: prune_old_snapshots</code>).
      </p>
    </div>
  </details>`;
}

export function metadataPage(data, state) {
  return `${schemaInfo()}${productCatalog(data, state)}`;
}
