# Frontend progress

**Status:** IN PROGRESS
**Last updated:** 2026-11-15 (US Central)

## Discover: universal saving + on-demand discovery UI (branch `iris/discover-ui`, Phase A)

Based on `origin/main` @ `362a377`, which includes PR #2. Frontend only: no backend, Databricks, or shared-contract files changed. The backend `GET /discover` endpoint is **not built yet** (it is waiting for backend-teammate approval), so discovery runs against a mock API. Not committed, pushed, or deployed as of this update.

### What changed
- **Universal saving.**
  - Searching a retailer product URL (http/https) always shows a "Save to My Collection" card, in demo and API mode, even when discovery fails.
  - The title comes from the URL path. The URL is stored but **never opened, fetched, or verified**, and its `#fragment` is dropped.
  - Rejected URLs: localhost, IP addresses, `.local`/`.internal` hosts, URLs with credentials, non-http(s) schemes, and URLs over 2048 characters.
- **Manual entry.** "Add it manually" forms under the search results and in My Collection take a name (required), retailer, URL, the price you saw (optional, $0–$100,000), and a category. The item saves immediately.
- **Local snapshot store.** `localStorage['findora-saved-discoveries']` = `{id → snapshot}`, with ids `url:<hash>`, `manual:<uuid>`, and `discovered:<id>`.
  - A `:` never appears in a canonical Gold `product_id`, so these never collide with catalog items and never call `/products/{id}`.
  - Every stored entry is re-validated on load; malformed entries, `javascript:` links, and invalid prices are dropped.
  - Canonical saves keep using `findora-saved-products` (unchanged).
- **My Collection.** Unverified items show alongside catalog items, with "Saved link", "Added by you", or "Unverified discovery" badges and their price wording.
  - Category filters, removal, and persistence across reloads all work.
  - "Reset saved items & budget" and "Delete profile" also clear the local store.
  - Free-text titles check coat/jacket words first, so "Hooded Parka" is filed under Jackets & coats. The catalog's `collectionCategory()` rule is unchanged.
- **Budget.** The calculation is unchanged: only exact USD catalog offers count. Unverified items are listed as "Unverified listing price ($X) — not counted" or "Price you entered — not counted".
- **Discover results (API mode).**
  - A non-empty search calls `GET /discover?q=`. If the API returns 404 (no discovery route), the app falls back to `/products/search`, shows a notice, and stops trying `/discover` until the mode changes.
  - An empty search still lists the catalog. Demo mode is unchanged, apart from URL saving and manual entry.
  - Results appear in three separate groups:
    - **In Findora catalog**: each card says "Possible catalog match · reason. Not confirmed as the exact item you searched for." High-scoring matches are never presented as exact.
    - **Discovered listings (Unverified)**: listed price, observation time, source/provenance, a link (a Google redirect shows as "View listing on Google Shopping"; placeholder hosts are never linked), and save.
    - **Similar in catalog**: alternatives with reasons; a null price shows "No current price". Clicking one opens the existing product detail flow.
  - A `discovery_status` banner covers unavailable, rate_limited, budget_exhausted, disabled, cached, and skipped_catalog_match. Mock responses always show a "MOCK DISCOVERY DATA" banner and a "Mock fixture" tag.
- **Unverified item detail.** No `/offers`, `/history`, or `/advice` requests are made. The view shows the stored listing (price labeled unverified, with source and timestamp), "Not tracked by Findora yet", and advice fixed at INSUFFICIENT DATA ("Unverified items are never used for buy/wait guidance").

### Mock API (dev/test only)
- `frontend/scripts/mock-api.mjs` (Node standard library; `npm run mock-api`, port 8001) implements the **proposed** `/discover` contract.
  - Catalog matches and similar items are computed by simple token scoring against the upstream catalog (`FINDORA_UPSTREAM`, default `http://127.0.0.1:8000`).
  - Discovered listings come from `frontend/mock/discover-fixtures.json`.
  - All other GET routes pass through to the upstream backend unchanged.
- The fixtures are synthetic. Every title contains "MOCK", every retailer ends in "(mock)", product links use `example.com` placeholders, and one scenario uses a dummy Google redirect URL (`https://www.google.com/url?q=mock-listing`) to exercise that display path.
- Trigger keywords: `mock-unavailable`, `mock-ratelimit`, `mock-error` (503), `mock-malformed`.
- Nothing in production points at the mock. `.env.example` still targets `:8000`, the default API URL is `http://localhost:8000`, and `vite build` outputs only `dist/index.html`, with no mock references (verified by grep).
- Proposed `/discover` response shape:
  - Top-level fields: `query`, `input_type`, `interpreted`, `catalog_matches[]` (Product + `match_reason`/`match_score`), `discovered[]`, `similar[]` (SimilarProduct), `discovery_status`, `notices[]`, and `mock` (mock only).
  - Each `discovered[]` entry: `candidate_id`, `title`, `retailer`, `listed_price`, `currency`, `url`, `url_kind`, `observed_at`, `provenance`, `verification: "unverified"`, `problems[]`.
  - It still needs team agreement and a `docs/decisions.md` entry before backend implementation.

### VERIFIED (local; mock and backend demo mode only — no SerpAPI, no Databricks)
- `npm run build`: passes. `git diff --check`: passes. `npm ci --dry-run`: the lockfile is consistent (no dependency changes; `package.json` only gains the `mock-api` script).
- Headless-Chrome suite (CDP, no new dependencies): **145/145 checks passed** in one full run.

| Suite | Setup | Result |
|---|---|---|
| Phase A–C regression (config, catalog, verified offers, history fallback, advice guards, errors, retry, malformed data, budget, onboarding/collection) | fixture API, backend demo mode, local demo | 97/97 |
| Discover via mock: URL saving (also during a 503), unsafe URL rejected, 3 result groups, labels, Google listing link, saving and detail view (no `/products/*` calls), manual entry and validation, filters, budget exclusion, removal and reload, malformed candidates, tampered storage, reset | mock-api → backend demo mode | 41/41 |
| Discover fallback (API without `/discover`) | fixture API | 3/3 |
| Discover in local demo mode (URL save + manual entry, no API calls) | none | 4/4 |

- Test scripts live outside the repo, in the session scratchpad, and are not committed.

### Known limitations / blockers
- **The backend `/discover` endpoint does not exist yet.** Real SerpAPI discovery, real catalog scoring, and non-null similar-item prices are untested. The backend branch (`iris/discover-api`) is waiting for teammate approval.
- The `/discover` contract is a proposal; shared docs (`docs/api-contract.md`, `docs/decisions.md`) are not updated yet.
- Unverified items live only in this browser (localStorage). They are not synced across devices and are lost if site data is cleared.
- There is no automated path from a saved discovery to a verified catalog product. Promotion uses the existing manual Databricks flow (manifest → collect → review → approve).
- The 24-hour freshness window and the Databricks-mode blockers below still apply to verified prices.

## Frontend → FastAPI integration (branch `iris/frontend-api-integration`)

Based on `origin/feature/frontend` @ `100f5dc`. Committed as `ff79bb1` and merged to `main` in PR #2 (`362a377`).

### Architecture and configuration
- The active app is the single self-contained `frontend/index.html` (inline CSS + script). Vite serves and builds it. `src/main.jsx` and `src/style.css` are starter files the page does not load; they are left untouched.
- **API base URL**, in priority order: runtime `window.FINDORA_API_URL` → build/dev env `VITE_API_URL` (Vite replaces the `%VITE_API_URL%` placeholder in `index.html` during `vite` and `vite build`) → `http://localhost:8000`. Malformed or non-http(s) values are ignored. If the variable is unset, Vite prints a harmless "not defined" warning and the fallback applies.
- **Data source**, in priority order: `?mode=api|demo` URL parameter → dropdown choice saved in localStorage → `VITE_DEFAULT_MODE` → `demo`. The dropdown is unchanged; when the URL carries `?mode=`, the dropdown keeps it in sync.
- `frontend/.env.example` documents both variables. Copy it to `frontend/.env.local`, which is git-ignored. VITE_ values are public and embedded in the page; never put credentials there.

### Endpoints consumed (shapes per `docs/api-contract.md`, unchanged)
| Route | Used for |
|---|---|
| `GET /products/search?q=` | Homepage catalog in API mode (empty `q`, cached until mode switch) and search (an empty query in API mode lists the catalog) |
| `GET /products/{id}` | Saved-collection rehydration |
| `GET /products/{id}/offers` | Offers panel; budget uses the lowest exact USD offer |
| `GET /products/{id}/history` | History chart/list, last-observed fallback, advice coverage |
| `GET /products/{id}/similar` | Similar products (`price: null` → "No current price") |
| `GET /products/{id}/advice` | Buy-or-wait card + readable evidence |

Advice `evidence` field names were taken from `backend/app/service.py` on `origin/codex/backend-databricks`: `observation_count`, `distinct_observation_dates`, `span_hours`, `first_observed_at`, `last_observed_at`, `current_lowest_price`, `median_observed_price`. Error bodies follow FastAPI's `{"detail": ...}` shape (404 `Unknown product`, 503 `Databricks data is unavailable; retry later.`).

### Changes completed
- **Phase A (API config + catalog):** env-based API URL and mode selection (above); API-mode Homepage loads the backend catalog, with loading, empty, and error states and Retry; empty API search lists the catalog; the API-mode banner shows the API base URL.
- **Phase B (verified prices):**
  - The "Verified real price" tag appears only for `match_type=exact` + `source_type` snapshot/live + price > 0 + valid `observed_at`.
  - Snapshots read "Snapshot observed … · not a live quote"; live offers read "Live source observed …".
  - Source links show the hostname. Demo and `example.com` links stay hidden.
  - When no verified fresh offer exists, a **Last observed price** card shows the newest real (snapshot/live) history observation, stating it is historical and not a currently verified retailer offer. Demo history never qualifies.
  - Advice is forced to INSUFFICIENT_DATA for any demo data, for under 3 UTC dates or under 48 h of real coverage, for no fresh verified offer, or for an unknown decision value.
  - Fixed `formatDate(null)` rendering as "Jan 1, 1970".
- **Phase C (robustness):**
  - Advice evidence is rendered as labeled values; null renders as "Not available", never $0, and demo evidence is marked illustrative.
  - Central `apiGet`: 404, 503 (Databricks unavailable), 4xx, and 5xx get distinct messages. The FastAPI `detail` is shown only when it is short and plain; tracebacks, tokens, URLs, and 422 validation lists are suppressed. Non-JSON or non-object bodies say "could not read". The CORS hint appears only on connection failures.
  - Per-section Retry refetches only that section and re-renders its dependents (history → offers + advice; offers → advice); other loaded sections are preserved.
  - Malformed array entries are filtered out; missing titles fall back to "Untitled product"; search results without a `product_id` are skipped.
  - Budget calculation is unchanged. Rows label "Real snapshot" vs "Seed demo price (illustrative)"; the total warns when demo prices are included; products without a current offer state "historical prices are not counted". Saved-item errors are short reasons (404, 503, unreachable).

### VERIFIED (local, reproducible; not Databricks-backed)
- `npm run build`: passes. `npm ci --dry-run`: `package-lock.json` is consistent with `package.json` (react 18.3.1, react-dom 18.3.1, vite 5.4.21).
- Headless-Chrome suite driven over the Chrome DevTools protocol with no new dependencies; **94/94 checks passed** in the final full run:

| Suite | Backend used | Result |
|---|---|---|
| Phase A main (config, modes, catalog, search, caching, dropdown, product detail) | backend branch, demo mode | 15/15 |
| Phase A backend down / env vars in dev server | none / backend demo mode | 2/2, 3/3 |
| Phase B verified fresh, demo-only, missing prices/timestamps, empty, spoofed BUY, valid BUY, offers 500 | fixture API, Columbia fresh | 24/24 |
| Phase B Columbia stale (last observed $220 card, no verified tag) | fixture API, Columbia stale | 6/6 |
| Phase B backend demo (demo labels, `/products/{id}`, 404) | backend branch, demo mode | 7/7 |
| Phase C evidence, 503 per section, section retry isolation, malformed bodies, unsafe detail, search errors, budget labels | fixture API | 23/23 |
| Phase C stale Columbia not counted in budget | fixture API | 3/3 |
| Phase C real backend 404/422, demo evidence, budget with demo + missing product | backend branch, demo mode | 5/5 |
| Local demo mode: onboarding, demo detail, Add to Collection, budget $47.99, My Collection | none | 6/6 |

- "Backend branch, demo mode" means `origin/codex/backend-databricks` @ `8b0bb29`, exported with `git archive` (no checkout or modification) and run with `FINDORA_DATA_MODE=demo`.
- "Fixture API" means a test-only, contract-shaped Python stdlib server kept outside the repo. Its Columbia $220 record mirrors the reviewed observation in `databricks/config/approvals.json`, with timestamps relative to now. The app contains no Columbia-specific code or prices.
- `git diff --check`: passes.

### Blocked / not verified
- **Databricks-mode integration is NOT tested.** It needs the backend's SQL warehouse HTTP path and credentials. Still unconfirmed against real Gold: Columbia `source_type`/URL/timestamp format, `data_status` values, the real catalog contents, and 503 behavior.
- The backend's own 31 pytest tests were not re-run here (pytest is not installed locally); that pass count is the backend teammate's report.

### Known limitations
- **24-hour freshness window (backend/Gold policy, unchanged):**
  - `/offers` only returns exact offers observed in the last 24 h. Seed demo offers dated `2026-11-14T12:00Z` drop out of Databricks-mode `/offers` after ~2026-11-15 12:00 UTC.
  - The Columbia observation (reviewed ~2026-11-15 03:21 UTC) will likely drop out ~24 h after its `observed_at`. After that the UI shows it as **Last observed price** and the budget does not count it.
  - The frontend's own local demo mode is unaffected.
- History observations have no `match_type` in the contract, so the last-observed card is tagged Real snapshot / Live source, never "Verified real price".
- In backend demo mode the catalog is headphones (`demo-headphones-*`), not the Gold clothing IDs, so clothing searches return 0 results until Databricks mode is live.
- Backend CORS defaults to `http://localhost:5173` only. Opening `127.0.0.1:5173`, a LAN IP, or a fallback Vite port is blocked unless `FINDORA_CORS_ORIGINS` includes it.
- The API-mode Homepage shows the whole catalog (backend caps it at 50) and is not filtered by profile interests.
- The budget counts an exact USD offer even when its `source_type` is missing (pre-existing logic, left unchanged; the row says "Source not provided").

### Requests for backend teammate
1. Run Databricks mode live and share curl output for `columbia-2088121-black-m-regular` (search, offers, history, advice).
2. Agree how the 24 h window should behave during the judged demo. Any change is a contract decision for `docs/decisions.md`; the frontend already degrades to "Last observed price".
3. Optionally align demo-mode fixtures with the Gold clothing IDs.
4. Add `http://127.0.0.1:5173` and the deployed frontend origin to `FINDORA_CORS_ORIGINS`.

### Local development and testing
```bash
# Backend (teammate's branch, without switching yours): detached worktree
git worktree add --detach ../findora-backend origin/codex/backend-databricks
cd ../findora-backend/backend && python3 -m pip install -r requirements.txt
FINDORA_DATA_MODE=demo python3 -m uvicorn app.main:app --port 8000
# Databricks mode: export FINDORA_DATA_MODE=databricks plus the variables in backend/README.md in your shell only

# Frontend
cd frontend && npm install
cp .env.example .env.local        # optional; edit VITE_API_URL / VITE_DEFAULT_MODE
npm run dev                       # open http://localhost:5173/?mode=api  (use localhost, not 127.0.0.1)
npm run build
```
Smoke checks: `curl -s localhost:8000/health` and `curl -s 'localhost:8000/products/search?q='`, then in the browser choose Live API, select a product, and confirm the offers, history, similar, and advice sections render.

## Verified completed (earlier frontend work)
- First-run onboarding requires a valid local profile before showing the app; choosing Other reveals a required custom clothing-interest field.
- Only a profile explicitly submitted through setup is treated as complete. Legacy or placeholder profiles do not skip onboarding; completed profiles persist on later visits.
- Profile changes persist locally. The Other collection filter uses the entered label and is omitted when Other is not selected.
- The search box is inside the Homepage welcome panel below the greeting, uses the requested clothing/brand/URL placeholder, and routes searches to Price Intelligence; it is hidden on other tabs.
- Search results do not open Product Intelligence automatically, including single-result searches; the detail view opens only after the user selects a catalog product button.
- Product Intelligence has an upper-right Add to Collection control that toggles saved state and stays synchronized with the catalog save button.
- My Collection filters saved demo products into all five standard clothing categories; each category was exercised in the browser.

## In progress
- Frontend remains in explicit synthetic Clothing demo mode by default; live API behavior has only been checked with contract-shaped mocks.
- Chrome extension files are split into a Manifest V3 unpacked-extension folder; loading and runtime behavior have not yet been verified in Chrome.

## Next steps
- Verify search and product detail against the integrated FastAPI backend when clothing records are available.
- Rehearse the full judge flow with the team’s integrated data.

## Blockers / dependencies
- No live backend validation was performed for this change; frontend behavior depends on an integrated API with supported clothing records.

## Changed files / tests and outcomes
- `frontend/index.html`: added the Other interest field, combined the Homepage-only search box and welcome into one panel, added My Collection category filters, and added the Product Intelligence collection control.
- Browser: verified profile gating, conditional/required Other input, saved-profile behavior, all standard collection filters, conditional Other filter, homepage-only search visibility and demo search routing; no page errors or duplicate IDs observed.
- Browser: verified single-result demo and mocked API searches keep Product Intelligence closed until the product button is selected.
- Browser: verified Add to Collection appears in the product detail header, adds/removes the product, and synchronizes the catalog save control and collection count.
- Browser: verified an old “Demo Shopper” profile opens onboarding, submitting a user profile opens Homepage, completed profiles return on reload, and a cleared profile starts at onboarding with the app and search hidden.
- Browser: verified the welcome panel contains the search box below the greeting, the removed subtitle is absent, the layout fits mobile without horizontal overflow, the search stays hidden on My Collection, and demo search still routes to results.
- `extension/manifest.json`, `extension/popup.html`, `extension/popup.css`, and `extension/popup.js`: replaced the concatenated `extension/extension.html` with a standard unpacked extension package; mock output is labeled synthetic.
- Extension validation: Python manifest/asset-reference/whitespace checks passed; `git diff --check` passed. `node --check extension/popup.js` could not run because Node.js is unavailable, and Chrome installation has not been tested in this environment.
- `git diff --check`: passed.

## Handoff notes
- No backend, Databricks, or shared contract files changed.
