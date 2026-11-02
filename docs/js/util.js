/* Small helpers shared by every component. */

/** Escape text before putting it into HTML. Use for every value that comes from the API. */
export function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** Availability band used for colours and store status. */
export function band(pct) {
  return pct >= 90 ? 'ok' : pct >= 80 ? 'warn' : 'crit';
}
export const BAND_LABEL = { ok: 'Healthy', warn: 'Watch', crit: 'Critical' };

/** Coloured pill. tone: crit | warn | ok | info | neutral | brand */
export function badge(tone, text, withDot = true) {
  return `<span class="badge b-${tone}">${withDot ? '<span class="dot"></span>' : ''}${esc(text)}</span>`;
}

/** 230 -> "3 hr 50 min", 45 -> "45 min" */
export function duration(minutes) {
  const h = Math.floor(minutes / 60), m = minutes % 60;
  if (!h) return `${m} min`;
  return m ? `${h} hr ${m} min` : `${h} hr${h > 1 ? 's' : ''}`;
}

/** "09:50" -> "9:50 am", "13:05" -> "1:05 pm" */
export function clock(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`;
}

/** 1240 -> "1,240" (Indian grouping) */
export function units(n) {
  return Number(n).toLocaleString('en-IN');
}

/** Legend swatch for a brand. */
export function swatch(colorVar) {
  return `<span class="sw" style="background:var(${colorVar})"></span>`;
}
