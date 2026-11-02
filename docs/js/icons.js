/* Line icons (24x24, stroke). Usage: icon('overview') or icon('search', 'sm') */

const PATHS = {
  logo: '<polyline points="3 12 7 12 10 5 14 19 17 12 21 12"></polyline>',
  overview: '<rect x="3" y="3" width="7" height="9" rx="1.5"></rect><rect x="14" y="3" width="7" height="5" rx="1.5"></rect><rect x="14" y="12" width="7" height="9" rx="1.5"></rect><rect x="3" y="16" width="7" height="5" rx="1.5"></rect>',
  stock: '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"></path><path d="M3 8l9 5 9-5"></path><path d="M12 13v8"></path>',
  competition: '<path d="M4 20V11"></path><path d="M10 20V4"></path><path d="M16 20v-7"></path><path d="M21 20H3"></path>',
  forecast: '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path>',
  alerts: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10 21a2 2 0 0 0 4 0"></path>',
  rules: '<path d="M4 7h10"></path><path d="M18 7h2"></path><circle cx="16" cy="7" r="2"></circle><path d="M4 17h4"></path><path d="M12 17h8"></path><circle cx="10" cy="17" r="2"></circle>',
  data: '<ellipse cx="12" cy="6" rx="8" ry="3"></ellipse><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"></path><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"></path>',
  updown: '<path d="M8 9l4-4 4 4"></path><path d="M16 15l-4 4-4-4"></path>',
  chevron: '<path d="M6 9l6 6 6-6"></path>',
  search: '<circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path>',
  pen: '<path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"></path>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path>',
  sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7"></path><path d="M21 4v5h-5"></path>',
  download: '<path d="M12 3v12"></path><path d="M7 10l5 5 5-5"></path><path d="M5 21h14"></path>',
  close: '<path d="M6 6l12 12M18 6L6 18"></path>',
  attention: '<path d="M12 9v4M12 17h.01"></path><circle cx="12" cy="12" r="9"></circle>',
  info: '<circle cx="12" cy="12" r="9"></circle><path d="M12 11v5"></path><path d="M12 8h.01"></path>'
};

export function icon(name, size = '') {
  return `<svg class="ic ${size}" viewBox="0 0 24 24" aria-hidden="true">${PATHS[name] || ''}</svg>`;
}
