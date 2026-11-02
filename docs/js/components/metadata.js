/* Metadata page - the raw underlying data behind every number on the
   dashboard (every tracked brand's products, with live inventory per
   store), for verification/transparency. Not part of the original
   canvas/data.js contract - see data.products and products.js. */
import { productCatalog } from './products.js';

export function metadataPage(data, state) {
  return productCatalog(data, state);
}
