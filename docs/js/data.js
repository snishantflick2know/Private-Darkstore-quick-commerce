/* =====================================================================
   SAMPLE DATA — this object is the API contract.
   GET /api/dashboard?platform=&region=&period=  should return JSON in
   exactly this shape. app.js fetches it and falls back to this sample
   if the API isn't running. Raw values only — all formatting
   (%, "3 hr 50 min", "9:50 am") happens in the components.
   ===================================================================== */

export const SAMPLE = {
  meta: {
    platform: 'Blinkit',            // Blinkit | Zepto | Instamart
    region: 'Delhi NCR',
    category: 'Juices',
    period: '7D',                   // Today | 7D | 30D
    updatedMinutesAgo: 4,
    storesChecked: 5,
    checkIntervalMinutes: 10,
    nextCheckMinutes: 6
  },

  brand: { name: 'Paper Boat', company: 'Hector Beverages', initials: 'PB', totalProducts: 34 },

  // Brand order is used by every per-brand array below. Index 0 = your brand.
  // colorVar must match a CSS variable in tokens.css.
  brands: [
    { name: 'Paper Boat',   colorVar: '--brand' },
    { name: 'Real',         colorVar: '--c-real' },
    { name: 'Raw Pressery', colorVar: '--c-raw' },
    { name: 'B Natural',    colorVar: '--c-bn' },
    { name: 'Tropicana',    colorVar: '--c-trop' }
  ],

  // Headline card
  headline: {
    availabilityPct: 86, previousPct: 89, rank: 4,
    productsInStock: 29,
    leaderName: 'Real', pointsBehindLeader: 7,
    hoursOffShelf: 29, hoursOffShelfChange: 6.5,
    averageOutageMinutes: 159
  },

  // 7-day availability, one array per brand (same order as brands)
  trend: {
    days: ['27 Oct', '28 Oct', '29 Oct', '30 Oct', '31 Oct', '1 Nov', '2 Nov'],
    series: [
      [91, 90, 89, 90, 88, 89, 86],
      [93, 94, 92, 93, 94, 93, 93],
      [90, 91, 92, 90, 91, 92, 91],
      [87, 88, 89, 88, 87, 88, 88],
      [82, 80, 81, 79, 80, 78, 79]
    ]
  },

  // Units on shelf at last check, per brand index; changePct vs 7 days ago
  stockOnShelf: [
    { brand: 0, units: 1240, changePct: -6 },
    { brand: 2, units: 1110, changePct: 3 },
    { brand: 1, units: 980,  changePct: 4 },
    { brand: 4, units: 660,  changePct: -2 },
    { brand: 3, units: 420,  changePct: 1 }
  ],

  // Four tiles. trend = last 7 data points for the sparkline.
  // tone: crit | warn | ok | brand (sparkline colour); deltaTone: bad | good
  tiles: [
    { label: 'Out of stock right now',  value: 5, unit: 'of 34',    delta: '2 more',   deltaTone: 'bad',  note: 'than the last check',      tone: 'crit',  trend: [2, 3, 2, 3, 3, 3, 5] },
    { label: 'Running out in 6 hours',  value: 2, unit: 'products', delta: '',         deltaTone: 'bad',  note: 'Kala Khatta and Jamun',    tone: 'warn',  trend: [0, 1, 1, 0, 1, 1, 2] },
    { label: 'Stock at nearby stores',  value: 2, unit: 'of 5',     delta: '10 units', deltaTone: 'good', note: 'ready to move',            tone: 'ok',    trend: [1, 1, 2, 1, 2, 2, 2] },
    { label: 'Competitors out of stock', value: 7, unit: 'products', delta: '2 more',  deltaTone: 'good', note: 'chances to win the shelf', tone: 'brand', trend: [4, 5, 4, 6, 5, 6, 7] }
  ],

  // Availability % per store, one value per brand (same order as brands).
  // map = position on the 320x190 schematic map (replace with lat/lng later).
  stores: [
    { name: 'Sohna Road',   city: 'Gurgaon',   values: [94, 96, 92, 90, 82], map: { x: 118, y: 162, lx: 132, ly: 166, anchor: 'start' } },
    { name: 'Lajpat Nagar', city: 'New Delhi', values: [82, 91, 93, 88, 76], map: { x: 188, y: 66,  lx: 188, ly: 50,  anchor: 'middle' } },
    { name: 'DLF Phase 3',  city: 'Gurgaon',   values: [88, 95, 90, 86, 80], map: { x: 56,  y: 112, lx: 56,  ly: 134, anchor: 'middle' } },
    { name: 'Saket',        city: 'New Delhi', values: [79, 92, 89, 87, 77], map: { x: 140, y: 100, lx: 126, ly: 104, anchor: 'end' } },
    { name: 'Sector 18',    city: 'Noida',     values: [87, 91, 91, 89, 80], map: { x: 268, y: 92,  lx: 268, ly: 114, anchor: 'middle' } }
  ],

  // Your products currently at 0 units. nearby.tone: ok | crit | neutral
  stockouts: [
    { product: 'Kala Khatta',    pack: '200 ml', mrp: 30, store: 'Saket',        since: '09:50', minutesOut: 230, outBetween: '08:50–09:50', outRange: '3h 50m–4h 50m', outDuringPeak: true, timesThisWeek: 2, nearby: { tone: 'ok',      text: '4 at store 49971' }, competitorInStock: 'Real' },
    { product: 'Aam Panna',      pack: '200 ml', mrp: 30, store: 'Lajpat Nagar', since: '10:15', minutesOut: 205, outBetween: '09:15–10:15', outRange: '3h 25m–4h 25m', outDuringPeak: false, timesThisWeek: 3, nearby: { tone: 'crit',    text: 'Out nearby too' },   competitorInStock: null },
    { product: 'Alphonso Mango', pack: '1 L',    mrp: 99, store: 'Lajpat Nagar', since: '11:38', minutesOut: 122, outBetween: '10:38–11:38', outRange: '2h 2m–3h 2m', outDuringPeak: false, timesThisWeek: 1, nearby: { tone: 'crit',    text: 'May be delisted' },  competitorInStock: 'Real' },
    { product: 'Aamras',         pack: '200 ml', mrp: 30, store: 'Sohna Road',   since: '11:42', minutesOut: 118, outBetween: '10:42–11:42', outRange: '1h 58m–2h 58m', outDuringPeak: false, timesThisWeek: 4, nearby: { tone: 'ok',      text: '6 at store 31719' }, competitorInStock: 'Real, Tropicana' },
    { product: 'Jaljeera',       pack: '250 ml', mrp: 35, store: 'Sohna Road',   since: '11:42', minutesOut: 118, outBetween: '10:42–11:42', outRange: '1h 58m–2h 58m', outDuringPeak: false, timesThisWeek: 2, nearby: { tone: 'neutral', text: 'Not sold nearby' },  competitorInStock: 'B Natural' }
  ],

  // Needs your attention. tone: crit | warn | brand; goTo = page id
  attention: [
    { tone: 'crit',  title: 'Aamras 200 ml is out at Sohna Road',          detail: 'Store 31719 nearby has 6 you could move over',      action: 'Transfer', goTo: 'stock' },
    { tone: 'warn',  title: 'Kala Khatta will run out in about 2½ hours',   detail: '3 left at Sohna Road, selling about 1 an hour',     action: 'Reorder',  goTo: 'forecast' },
    { tone: 'brand', title: "Real has stock where you don't",               detail: 'Their Mixed Fruit 1 L is on the shelf at Sohna Road', action: 'Compare',  goTo: 'competition' },
    { tone: 'crit',  title: 'Alphonso Mango 1 L may have been delisted',    detail: 'Gone from the Lajpat Nagar listing since 11:38 am', action: 'Check',    goTo: 'alerts' }
  ],

  // Stock-outs page
  hoursOffShelf: [
    { product: 'Aamras 200 ml', hours: 11.5 },
    { product: 'Aam Panna 200 ml', hours: 8 },
    { product: 'Jaljeera 250 ml', hours: 5 },
    { product: 'Kala Khatta 200 ml', hours: 4.5 }
  ],
  stockoutsByStore: [
    { store: 'Sohna Rd', count: 6 }, { store: 'Lajpat Ngr', count: 5 }, { store: 'DLF Ph 3', count: 1 },
    { store: 'Saket', count: 3 }, { store: 'Sector 18', count: 1 }
  ],

  // Competition page — per brand index
  comparison: [
    { brand: 1, availabilityPct: 93, previousPct: 92, products: 22, outNow: 1 },
    { brand: 2, availabilityPct: 91, previousPct: 90, products: 28, outNow: 2 },
    { brand: 3, availabilityPct: 88, previousPct: 88, products: 12, outNow: 1 },
    { brand: 0, availabilityPct: 86, previousPct: 89, products: 34, outNow: 5 },
    { brand: 4, availabilityPct: 79, previousPct: 81, products: 15, outNow: 3 }
  ],
  competitorStockouts: [
    { product: 'Real Mixed Fruit',         pack: '1 L', store: 'Lajpat Nagar', minutesOut: 120, outRange: '2h–3h', yourOption: 'Mixed Fruit 1 L' },
    { product: 'Tropicana Orange Delight', pack: '1 L', store: 'Sohna Road',   minutesOut: 118, outRange: '1h 58m–2h 58m', yourOption: null },
    { product: 'B Natural Guava',          pack: '1 L', store: 'Saket',        minutesOut: 45,  outRange: '45 min–1h 45m', yourOption: 'Guava Twist' }
  ],

  // Forecast page
  forecast: [
    { product: 'Kala Khatta',   pack: '200 ml', store: 'Sohna Road',   unitsLeft: 3,  sellingPerHour: 1.2, hoursLeft: 2.5 },
    { product: 'Jamun',         pack: '200 ml', store: 'Lajpat Nagar', unitsLeft: 5,  sellingPerHour: 0.8, hoursLeft: 6 },
    { product: 'Litchi',        pack: '200 ml', store: 'DLF Phase 3',  unitsLeft: 9,  sellingPerHour: 0.9, hoursLeft: 10 },
    { product: 'Coconut Water', pack: '200 ml', store: 'Saket',        unitsLeft: 12, sellingPerHour: 0.7, hoursLeft: 17.1 }
  ],

  // Full product catalog (not part of the original canvas contract - added
  // so the individual-product/inventory view has sample data too when the
  // backend isn't running).
  products: [
    { brand: 'Paper Boat', product: 'Paper Boat Aamras Mango Drink', pack: '200 ml', store: 'Sohna Road', merchantId: '1234', mrp: 35, price: 30, inventory: 0, status: 'Out of stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'Paper Boat', product: 'Paper Boat Jaljeera', pack: '250 ml', store: 'Sohna Road', merchantId: '1234', mrp: 40, price: 35, inventory: 2, status: 'In stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'Paper Boat', product: 'Paper Boat Kala Khatta', pack: '200 ml', store: 'Sohna Road', merchantId: '1234', mrp: 35, price: 30, inventory: 3, status: 'In stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'Real', product: 'Real Mixed Fruit Juice', pack: '1 L', store: 'Sohna Road', merchantId: '1234', mrp: 125, price: 110, inventory: 14, status: 'In stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'Tropicana', product: 'Tropicana Orange Delight', pack: '1 L', store: 'Sohna Road', merchantId: '1234', mrp: 130, price: 115, inventory: 0, status: 'Out of stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'B Natural', product: 'B Natural Guava', pack: '1 L', store: 'Lajpat Nagar', merchantId: '35554', mrp: 120, price: 105, inventory: 6, status: 'In stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'Raw Pressery', product: 'Raw Pressery Cold Pressed Juice', pack: '250 ml', store: 'Lajpat Nagar', merchantId: '35554', mrp: 110, price: 95, inventory: 9, status: 'In stock', capturedAt: '03 Nov, 00:21 IST' }
  ],

  // Raw append-only snapshot history (same fields as products, but one row
  // per scrape run rather than deduplicated to latest - see server.py).
  snapshotHistory: [
    { brand: 'Paper Boat', product: 'Paper Boat Jaljeera', pack: '250 ml', store: 'Sohna Road', merchantId: '1234', mrp: 40, price: 35, inventory: 2, status: 'In stock', capturedAt: '03 Nov, 00:21 IST' },
    { brand: 'Paper Boat', product: 'Paper Boat Jaljeera', pack: '250 ml', store: 'Sohna Road', merchantId: '1234', mrp: 40, price: 35, inventory: 3, status: 'In stock', capturedAt: '02 Nov, 23:21 IST' },
    { brand: 'Paper Boat', product: 'Paper Boat Jaljeera', pack: '250 ml', store: 'Sohna Road', merchantId: '1234', mrp: 40, price: 35, inventory: 4, status: 'In stock', capturedAt: '02 Nov, 22:21 IST' }
  ],

  // Alerts page. type must be one of the keys in ALERT_TONE (components/alerts.js)
  alerts: [
    { time: '11:42', type: 'Out of stock',   text: 'Aamras 200 ml ran out at Sohna Road.' },
    { time: '11:42', type: 'Running low',    text: 'Only 2 Jaljeera 250 ml left at Sohna Road.' },
    { time: '11:40', type: 'New product',    text: 'Guava Twist 200 ml is now listed at Lajpat Nagar.' },
    { time: '11:38', type: 'Delisted',       text: 'Alphonso Mango 1 L has disappeared from the Lajpat Nagar listing.' },
    { time: '11:35', type: 'Competitor gap', text: 'Real has Mixed Fruit 1 L at Sohna Road, but yours is sold out.' },
    { time: '10:58', type: 'Back in stock',  text: 'Litchi 200 ml is back at Sohna Road.' }
  ]
};
