// DEV/TEST ONLY — mock implementation of the proposed `GET /discover` contract.
// Serves synthetic, clearly labeled fixtures (frontend/mock/discover-fixtures.json) and passes every
// other GET route through to the real FastAPI backend, so /products/* keep their real behavior.
// Catalog matches and similar items are computed from the upstream catalog with simple token scoring
// (a stand-in for the planned backend logic). Similar-item prices are always null here.
// Node standard library only. Never deploy this.
//
// Usage (from frontend/):
//   FINDORA_UPSTREAM=http://127.0.0.1:8000 MOCK_API_PORT=8001 npm run mock-api
//   VITE_API_URL=http://127.0.0.1:8001 npm run dev   # then open http://localhost:5173/?mode=api
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const FIXTURES = JSON.parse(readFileSync(fileURLToPath(new URL('../mock/discover-fixtures.json', import.meta.url)), 'utf8'));
const PORT = Number(process.env.MOCK_API_PORT || 8001);
const UPSTREAM = (process.env.FINDORA_UPSTREAM || 'http://127.0.0.1:8000').replace(/\/+$/, '');
const MOCK_NOTICE = 'MOCK DISCOVERY DATA — synthetic fixtures, not real listings or prices.';
const STOP = new Set(['a', 'an', 'the', 'and', 'or', 'for', 'with', 'in', 'of', 'to', 'mens', 'men', 'womens', 'women', 'unisex',
  'size', 'color', 'new', 'buy', 'cheap', 'best', 'www', 'com', 'http', 'https', 'html', 'p', 'dp', 'product', 'products', 'item']);
const LEXICON = [
  ['sweatshirts', /^(hoodie|hoodies|sweatshirt|sweatshirts|fleece|crewneck|pullover)$/],
  ['outerwear', /^(parka|jacket|jackets|coat|coats|shell|rain|windbreaker|vest)$/],
  ['tops', /^(tee|tees|t|shirt|shirts|top|tops|blouse)$/],
  ['denim', /^(jean|jeans|denim)$/],
  ['accessories', /^(beanie|hat|cap|scarf|belt|bag|gloves)$/],
  ['audio', /^(headphone|headphones|earbud|earbuds|audio|speaker)$/],
];

const tokens = (text) => String(text || '').toLowerCase().split(/[^a-z0-9]+/).filter((t) => t && !STOP.has(t) && (!/^\d+$/.test(t) || t.length >= 4));
const categoryOf = (words) => LEXICON.find(([, re]) => words.some((w) => re.test(w)))?.[0] || null;

function interpret(q) {
  try {
    const url = new URL(q);
    if (['http:', 'https:'].includes(url.protocol) && url.hostname.includes('.')) {
      const host = url.hostname.replace(/^www\./, '');
      let path = url.pathname;
      try { path = decodeURIComponent(path); } catch { /* raw */ }
      const terms = [...new Set([host.split('.')[0], ...tokens(path)])];
      return { input_type: 'url', terms, retailer_host: host };
    }
  } catch { /* not a URL */ }
  return { input_type: 'text', terms: [...new Set(tokens(q))], retailer_host: null };
}

async function upstreamCatalog() {
  const response = await fetch(`${UPSTREAM}/products/search?q=`, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`upstream ${response.status}`);
  const body = await response.json();
  return Array.isArray(body.items) ? body.items.filter((p) => p && typeof p.product_id === 'string') : [];
}

async function discover(q) {
  const interpreted = interpret(q);
  const notices = [MOCK_NOTICE];
  let catalog = [];
  try {
    catalog = await upstreamCatalog();
  } catch {
    notices.push('MOCK: the upstream catalog could not be reached, so no catalog matches or similar items are shown.');
  }
  const queryCategory = categoryOf(interpreted.terms);
  const scored = catalog.map((product) => {
    const words = new Set(tokens(`${product.title} ${product.brand} ${product.category}`));
    const overlap = interpreted.terms.filter((t) => words.has(t));
    return { product, overlap, score: interpreted.terms.length ? overlap.length / interpreted.terms.length : 0, category: categoryOf([...words]) };
  });
  const matches = scored.filter((s) => s.overlap.length >= 2 && s.score >= 0.5).sort((a, b) => b.score - a.score).slice(0, 5);
  const matchIds = new Set(matches.map((m) => m.product.product_id));
  const similar = scored
    .filter((s) => !matchIds.has(s.product.product_id))
    .map((s) => {
      const sameCategory = queryCategory && s.category === queryCategory;
      const sameBrand = s.product.brand && interpreted.terms.includes(String(s.product.brand).toLowerCase());
      return { ...s, rank: (sameCategory ? 2 : 0) + (sameBrand ? 1 : 0), sameCategory, sameBrand };
    })
    .filter((s) => s.rank > 0)
    .sort((a, b) => b.rank - a.rank)
    .slice(0, 3)
    .map((s) => ({
      product_id: s.product.product_id, title: s.product.title, brand: s.product.brand, price: null,
      reason: `${[s.sameCategory && `Same category (${queryCategory})`, s.sameBrand && 'same brand'].filter(Boolean).join(' and ')}; an alternative, not the item you searched for.`,
    }));

  const haystack = `${q.toLowerCase()} ${interpreted.terms.join(' ')}`;
  const scenario = FIXTURES.scenarios.find((s) => s.match.some((m) => haystack.includes(m))) || FIXTURES.default;
  if (scenario.http_status) return { status: scenario.http_status, body: { detail: scenario.detail } };
  let status = scenario.discovery_status;
  let discovered = (scenario.discovered || []).map((c) => (c && typeof c === 'object' && !Array.isArray(c) && c.provenance && !c.observed_at
    ? { ...c, observed_at: FIXTURES.observed_at } : c));
  if (matches.some((m) => m.score >= 0.75) && scenario === FIXTURES.default) {
    status = 'skipped_catalog_match';
    discovered = [];
  }
  notices.push(...(scenario.notices || []));
  return {
    status: 200,
    body: {
      mock: true,
      query: q,
      input_type: interpreted.input_type,
      interpreted: { terms: interpreted.terms, retailer_host: interpreted.retailer_host, category: queryCategory },
      catalog_matches: matches.map((m) => ({ ...m.product, match_score: Math.round(m.score * 100) / 100,
        match_reason: `${m.overlap.length} of ${interpreted.terms.length} search terms match the title, brand, or category` })),
      discovered,
      similar,
      discovery_status: status,
      notices,
    },
  };
}

function send(res, origin, status, body, type = 'application/json') {
  res.writeHead(status, { 'Content-Type': type, 'Access-Control-Allow-Origin': origin || '*', Vary: 'Origin' });
  res.end(typeof body === 'string' ? body : JSON.stringify(body));
}

createServer(async (req, res) => {
  const origin = req.headers.origin;
  const url = new URL(req.url, 'http://mock.local');
  if (req.method === 'OPTIONS') {
    res.writeHead(204, { 'Access-Control-Allow-Origin': origin || '*', 'Access-Control-Allow-Methods': 'GET', 'Access-Control-Allow-Headers': '*' });
    return res.end();
  }
  if (req.method !== 'GET') return send(res, origin, 405, { detail: 'Method Not Allowed' });
  if (url.pathname === '/discover') {
    const q = (url.searchParams.get('q') || '').trim();
    if (q.length < 2 || q.length > 500) {
      return send(res, origin, 422, { detail: [{ loc: ['query', 'q'], msg: 'q must be 2-500 characters', type: 'value_error' }] });
    }
    const result = await discover(q);
    return send(res, origin, result.status, result.body);
  }
  try {
    const upstream = await fetch(`${UPSTREAM}${url.pathname}${url.search}`, { signal: AbortSignal.timeout(10000) });
    return send(res, origin, upstream.status, await upstream.text(), upstream.headers.get('content-type') || 'application/json');
  } catch {
    return send(res, origin, 502, { detail: 'Mock API could not reach the upstream backend.' });
  }
}).listen(PORT, '127.0.0.1', () => {
  console.log(`MOCK discovery API on http://127.0.0.1:${PORT} (upstream ${UPSTREAM}) — dev/test only`);
});
