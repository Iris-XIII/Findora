# Findora 💎 — Discover what's worth buying, where, and when

Findora is a shopping price-intelligence app built for MadHacks 2026 (Databricks track). You search for a clothing product. Findora shows exact-match retailer offers, observed price history, similar alternatives, and buy/wait guidance. Every price is labeled with where it came from.

**Live Databricks App:** https://findora-7474652186980812.aws.databricksapps.com
(Databricks Apps require a Databricks login with access to the workspace. If you can't open it, see the demo video and the local demo instructions below.)

**Demo App***: https://findora-pink.vercel.app/

## What makes Findora different
- **Every price shows how it was verified.** A price is shown as *Verified real price* only after it passes an exact-match review: same brand, model, color, size and condition, in USD, with a timestamp. Everything else is labeled clearly: last observed, unverified listing, price you entered, or seed demo.
- **Findora doesn't guess.** BUY or WAIT advice is shown only when there's a fresh verified offer *and* at least 3 distinct UTC dates of verified history spanning 48 hours. Otherwise the decision is `INSUFFICIENT_DATA`, with a plain explanation such as "View available offer" or "Price check pending".
- **Databricks holds the data.** Raw provider responses go to Bronze, reviewed and normalized offers to Silver, and served views to Gold. The live app reads Gold through Databricks SQL.

## Features
- **Discover:** search by product name, natural language, or a retailer URL. Results appear in three separate groups: *catalog matches*, *unverified listings* (on-demand discovery), and *similar alternatives*.
- **Product details:** current offers, a price-history chart, similar items, and evidence-based advice, with the evidence counts shown. Each section loads and retries on its own.
- **Verified price intelligence:** current offers come from Gold `current_offers`. When there's no fresh offer, the newest observation appears as "Last observed price", never as a current price.
- **My Collection:** save catalog products, discovered listings, pasted retailer links, or items you add by hand. Unverified items are badged.
- **Budget tracking:** totals only exact-match USD offers. Unverified prices are listed but marked "not counted".
- **URL saving:** you can always save any retailer link. Findora stores it but never opens or scrapes it.
- **Product images:** curated official manufacturer photos, keyed by exact product ID and color. Images identify the product only; they are never used as price evidence. Products without a verified image show a neutral placeholder.

## Tech stack
| Layer | Technology |
|---|---|
| Frontend | Vite (React/Vite project). The shipped UI is a single-page app in `frontend/index.html` written in plain JavaScript. |
| API | Python, FastAPI, Uvicorn (`backend/app`) |
| Data | Databricks (Free Edition), Unity Catalog, Delta tables, Bronze/Silver/Gold notebook pipeline (`databricks/`) |
| Serving | Databricks SQL warehouse via `databricks-sql-connector`, signed in with the Databricks SDK |
| Hosting | Databricks Apps: FastAPI serves the API and the compiled frontend from one origin (`deploy/findora-app`) |
| Price sources | SerpAPI (Google Shopping and Amazon product data), collected in batches and reviewed before entering Silver. Optional on-demand discovery via `/discover`. |

## Architecture
```text
SerpAPI snapshots ──► Bronze  serpapi_raw / raw_offers          (raw responses, unchanged)
                        │  review: exact brand/model/color/size/condition, USD, evidence URL
                        ▼        (config/approvals.json; only confirmed=true entries pass)
                      Silver  canonical_products / normalized_offers
                        ▼
                      Gold    product_catalog · current_offers (≤24 h) · product_offers
                              price_summary · price_coverage
                        ▼  Databricks SQL (read-only, bound parameters)
Browser ◄── Databricks App: FastAPI (/products/*, /discover) + compiled frontend
```

### Verified offers vs. unverified discoveries
| | Verified offer | Unverified discovery |
|---|---|---|
| Source | Gold `current_offers` / `product_offers` | `/discover` search result, a pasted link, or a manual entry |
| Requirements | `match_type=exact`, `source_type` snapshot/live, USD, price > 0, timestamp, approved review | None. Shown as is, with labels. |
| Shown as | "Verified real price" / "Last observed price" | "Unverified listing", "Saved link", "Added by you" |
| Counts in budget and advice | Yes | Never |

**Freshness:** a current offer must be no more than **24 hours** old. After that it drops out of current offers and appears as "Last observed price". Advice then becomes `INSUFFICIENT_DATA` until a new reviewed observation arrives.

## Run locally
Requires Python 3.11+ and Node 20+.

```bash
# API (demo data by default; set FINDORA_DATA_MODE=databricks for Gold)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000        # docs: http://localhost:8000/docs

# Frontend
cd frontend
npm install
cp .env.example .env.local                        # VITE_API_URL, VITE_DEFAULT_MODE
npm run dev                                       # http://localhost:5173 (add ?mode=api)
npm run mock-api                                  # optional: labeled MOCK /discover fixtures on :8001
```

Databricks mode needs `FINDORA_DATA_MODE=databricks`, `DATABRICKS_HTTP_PATH`, `FINDORA_CATALOG`, and Databricks SDK credentials (for example a `databricks auth login` profile). Optional on-demand discovery needs `SERPAPI_API_KEY` in the API's environment. Never commit `.env` files or keys.

## Tests and build
```bash
cd backend && python -m pytest tests -q                              # API, pricing guards, discovery (fake provider)
cd databricks && python3 -m unittest discover -s tests -v             # pipeline, review, Amazon adapter
python3 -m unittest discover -s deploy/findora-app/tests -v           # App diagnostics (from repo root)
cd frontend && npm run build                                          # production build -> frontend/dist
scripts/smoke_test.sh http://localhost:8000                           # demo-mode API smoke test
```

## Deploy the Databricks App
```bash
scripts/build_databricks_app.sh            # npm ci + build + package into build/databricks-app (with secret scan)
databricks workspace import-dir build/databricks-app /Workspace/Users/<you>/findora-app --overwrite
databricks apps deploy findora --source-code-path /Workspace/Users/<you>/findora-app
```
The App needs a SQL warehouse resource with key `sql-warehouse` (Can use). Its service principal needs `USE CATALOG` on `findora_hackathon`, `USE SCHEMA` on `gold`, and `SELECT` on the Gold objects. `app.yaml` holds no secrets. Data pipeline setup is in [`databricks/README.md`](databricks/README.md).

## Demo script
1. Open the App (or run locally with `?mode=api`) and search **"Columbia Marquam Peak parka"**.
2. Open the Columbia catalog match. It shows the official product photo, a **$220.00 Columbia Sportswear** offer tagged *Verified real price · Exact match · Real snapshot* (while within 24 hours of the observation), its price history, and advice of `INSUFFICIENT_DATA` / "View available offer", because one observation date isn't enough for buy/wait timing.
3. Open **Gildan 18000**. There's no verified offer: a conflicting Amazon listing is deliberately held as unverified pending a product-page check, so the advice is "Price check pending".
4. Paste any retailer URL into search. You can save it to My Collection immediately; it's badged unverified and the budget doesn't count it.
5. Open **My Collection** and **Budget**. Only exact-match USD offers are totaled.

## Known limitations
- **Live SerpAPI discovery is implemented but not enabled in production.** No SerpAPI key is configured in the App, so `/discover` returns catalog matches with "Live discovery is not configured".
- **The catalog is intentionally small:** 4 canonical products. Only Columbia 2088121 has an approved verified observation (a single snapshot), so buy/wait timing can't be computed yet.
- **Freshness:** verified prices expire from current offers 24 hours after observation. A new reviewed collection run is needed to keep them current.
- **Images:** 2 of 4 products have curated manufacturer photos, hotlinked from official store CDNs. The others show a placeholder.
- **Discovery matching:** catalog matching is a simple keyword overlap, so weak "possible matches" can appear. They're labeled as not confirmed.
- **Databricks Free Edition:** Apps may stop after 24 hours (restart with `databricks apps start findora`), compute quotas apply, and App access requires workspace or account permissions.
- **Saved items** live in the browser's localStorage, not on a server.

## Repository map
`frontend/` web app · `backend/` FastAPI · `databricks/` collection, review, and Bronze/Silver/Gold pipeline · `deploy/findora-app/` App entry point · `scripts/` packaging and smoke tests · `docs/` design, contracts, decisions, and per-role progress ([`AGENTS.md`](AGENTS.md) has the team workflow).
