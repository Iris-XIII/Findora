# Databricks progress

**Status:** MERGED into `integration/databricks-unified` (2026-11-15) — both tracks below preserved; unified refactoring pending (see Unified integration status at bottom)
**Last updated:** 2026-11-15

## Track A — Seed demo pipeline (branch `Iris_databrick_pipeline`, cloud-verified 2026-11-14)

## Verified completed

### Unity Catalog namespace (as proposed in docs/data-contract.md)
- Catalog `findora_hackathon` with schemas `bronze`, `silver`, `gold` — created and confirmed via `information_schema.schemata`.

### Pipeline scripts (databricks/sql/, run in order)
- `01_bronze.sql` — `bronze.raw_offers` DDL per data contract + 26 labeled seed-demo rows (5 clothing products, 6 fictional retailers, 3 dated observations per product, all `provenance` = `seed-demo: ...`, URLs are example.com placeholders).
- `02_silver.sql` — `silver.canonical_products` (5 rows) and `silver.normalized_offers` (26 rows) rebuilt from Bronze. `product_id` = `lower(brand)-lower(model-normalized)` e.g. `northpeak-fp-hood-100`. `match_type='exact'` only when raw variant equals canonical variant (mode per product); otherwise `unverified`.
- `03_gold.sql` — `gold.product_offers` (26 rows; price>0, USD-only filter, dedup, `source_type='demo'` from seed provenance) and `gold.price_summary` (5 rows, **verified (exact-match) offers only** per design.md "cheapest means lowest verified listed price"; products with no verified offers would appear with NULL stats and `observation_count=0`).

### Validation evidence (run on serverless SQL, 2026-11-14)
- Row counts: bronze.raw_offers=26, silver.canonical_products=5, silver.normalized_offers=26, gold.product_offers=26, gold.price_summary=5.
- `product_id` consistency: 0 canonical IDs missing from gold.product_offers / gold.price_summary; 0 silver offer IDs missing from canonical. No cross-layer drift.
- Seed labeling: 0 bronze rows without `seed-demo` provenance; 0 gold rows with `source_type <> 'demo'`. Unverified offers preserved: 1 (MegaMart hoodie size-M near-match, `match_type='unverified'`, kept in gold.product_offers, excluded from price_summary).
- Trace (bronze -> silver -> gold): Campus Apparel hoodie offer 47.99 @ 2026-11-14T12:00:00Z appears identically in all three layers; gold.price_summary lowest for `northpeak-fp-hood-100` = 47.99.
- `databricks/sql/validation.sql` executed: all counts returned as above; note its `lowest_price` column is a raw MIN over all offers incl. unverified (44.99 for the hoodie) — the verified statistic is `gold.price_summary.lowest_observed_price` (47.99).
- Verified-only aggregation correction to `gold.price_summary` explicitly approved by teammate 2026-11-14: unverified offers stay in `gold.product_offers` but never drive verified price stats.

## Gold objects for backend handoff (Person C)
- `findora_hackathon.gold.product_offers` — offer_id, product_id, retailer, price, currency, product_url, observed_at, match_type (exact/unverified), source_type (demo).
- `findora_hackathon.gold.price_summary` — product_id, lowest_observed_price, median_observed_price, minimum_observed_price, observation_count, last_observed_at (verified-only stats).
- `findora_hackathon.silver.canonical_products` — product_id, title, brand, category, model, image_url (NULL), attributes_json.
- Canonical product IDs: `northpeak-fp-hood-100`, `trailcraft-tc-rs-200`, `basicsco-bc-tee-300`, `denimworks-dw-jn-400`, `northpeak-np-bn-500`.
- Buy/wait advice inputs: median vs current lowest; return INSUFFICIENT_DATA when observation_count < 3 (all seed products have >= 5).

## In progress
- None at commit time.

## Next steps
- Backend (Person C): Databricks adapter for `/products/search`, `/products/{id}/offers`, `/history`, `/advice` reading the Gold objects above; switch `data_mode` from demo to observed once verified.
- Replace/augment seed data with documented real data sources (provenance + original URLs + collection method) when chosen.
- Databricks App (small product lookup on Gold data) — NOT deployed yet, deliberately deferred per team decision 2026-11-14; remember Free Edition apps stop after 24h — redeploy/check Sunday morning before 2 PM judging.

## Blockers / dependencies
- Awaiting decision on real product/price source and historical dataset (docs/design.md open decision).
- All current data is labeled seed-demo — must not be presented as observed retailer data.

## Changed files / tests and outcomes
- 2026-11-14: added `databricks/sql/01_bronze.sql`, `02_silver.sql`, `03_gold.sql`; executed on serverless SQL; validation queries above all passed (counts, ID consistency, labeling, layer trace, validation.sql). `bronze_template.sql` kept as reference template. No shared contract files modified.
## Track B — SerpAPI real-data pipeline (branch `codex/databricks-serpapi`)

### Local verification evidence
- User reports a successful Databricks Run All: Bronze 130, canonical products 3,
  normalized offers and all offer/summary Gold views 0. This is ingestion evidence,
  not verification of exact offers, backend integration, or App deployment.
- `python3 -m unittest discover -s tests -v` from `databricks/`: 33 tests passed.
- `python3 -m findora_data.collect --dry-run`: 3 targets, request ceiling 9; no API calls.
- `python3 -m compileall -q findora_data app notebooks`: passed.
- `git diff --check`, Python AST/config JSON validation, and new-file whitespace checks: passed.
- These are local checks only. No cloud integration is marked VERIFIED.
- Live responses collected by user: 11 files across two batches, 130 unique candidates,
  3 configured products, and 0 approved exact offers, validated by the local normalizer.
- `python3 -m findora_data.package_upload`: built `databricks/data/upload/findora_databricks_upload.zip`.
  Manifest records source hashes and expected counts; archive excludes private `.env` and unrelated files.
- Tests now also cover Google redirects, private key loading, credential exclusion, and immutable snapshot copying.
- Notebook bootstrap tests cover repo-root and nested working directories, notebook-context paths,
  explicit path overrides, and missing supporting files. Context access in the real serverless
  workspace is still unverified; the explicit `project_root` widget remains the fallback.

## Implemented locally
- Standard-library SerpAPI collector: Shopping discovery then Immersive Product stores,
  bounded request budget, credential redaction, partial-run retention, provider timestamps.
- Three configurable search targets: jacket, coat/parka, sweatshirt. Assumed men's black
  size M Regular. Official style references are recorded; prices/stock are not invented.
- Review queue and strict approvals for exact model/color/size/condition/currency,
  merchant evidence, available variant, and applicable price. No title-only exact matching.
- Databricks ingestion notebook and Delta persistence, with idempotent observations,
  complete-archive checks, and canonical identity protection.
- Contract-shaped Bronze/Silver/Gold objects plus current-offer, catalog, and coverage views.
- Streamlit Databricks App using service-principal SQL access; no SerpAPI key in the app.
- SQL validation, backend query examples, and a Free Edition setup/runbook.
- Direct ZIP import workflow, with notebook copying included snapshots into a Unity Catalog Volume.
- Private local `.env` support for future collection. Created an empty owner-only `.env`;
  no key was copied from chat. It is ignored by Git and excluded from the upload package.

## Next steps
0. Focus on one unisex Gildan 18000 Black adult M single-unit sweatshirt. Use
   `config/focus_products.json` for at most 3 collection requests; keep the full
   manifest for ingestion. Existing IDs/history are preserved; canonical count becomes 4.
1. Initial implementation published as `1d749b1` on `codex/databricks-serpapi`.
   User should Pull this branch and open the notebook inside the Git folder.
2. Select the branch, open `databricks/notebooks/01_ingest`, run its setup cell on serverless compute,
   then upload all 11 raw JSON files into `/Volumes/workspace/bronze/serpapi_raw/responses` and Run All.
3. Record actual cloud counts and rerun to verify stable observation counts.
4. Review real variant/price evidence and record approvals. Seek two retailers for one target.
5. Confirm canonical IDs and proposed query semantics with C; verify a backend Gold query.
6. Deploy App, grant warehouse/data permissions, verify judge access and record URL.
7. Add compatible alternatives once real coverage is known; C owns their ranking.

## Blockers / dependencies
- User confirmed Databricks Free Edition and jacket/coat/sweatshirt categories.
- User supplied the Free Edition workspace URL and screenshot confirming catalog `workspace`.
  ZIP import failed with `Path (undefined/findora_databricks_upload) doesn't start with '/'`.
  User requested a separate Git branch as the fallback. No authenticated Databricks access
  is available to this agent; cloning in Databricks and first notebook run remain user steps.
- Real source responses exist; approvals are still empty. User reported successful
  cloud ingestion; populated Gold offers and App deployment are still unverified.
- User's first notebook run failed to locate the code folder. Its error text matches the older
  ZIP notebook. Added ancestor/context discovery and explicit instructions to open the Git copy.
  The supplied notebook browser URL identifies an object, but does not reveal its workspace path.
- Store links in these responses use Google `/goto` redirects. Review queue now provides
  clickable links and permits only explicitly reviewed merchant destinations. One tested
  redirect led to a different size/color; no exact match was inferred from its title.
- No verified historical price dataset: start snapshot collection and report insufficient history.
- Current 3 targets span categories; they do not guarantee two similar alternatives per product.
- Cloud runtime and permission behavior remain unverified.

## Changed files / tests and outcomes
- Added `databricks/findora_data/`, `config/`, `notebooks/`, `app/`, `tests/`, and local `.gitignore`.
- Expanded `databricks/README.md` and SQL setup/validation; added `sql/backend_queries.sql`.
- Updated this role's progress only; shared contracts, frontend, and backend were not edited.
- Tests use explicitly synthetic fixtures confined to `tests/`; default manifests contain no prices.
- Added `findora_data/package_upload.py`, `tests/test_upload.py`, `.env.example`, and `UPLOAD.md`.
  Updated `01_ingest.py` to support imported snapshots and display the candidate review table.
### Handoff notes (Track B)
- Runtime catalog: `workspace`; user reported a successful write/read notebook run.
- `gold.product_offers` is historical approved snapshots; `gold.current_offers` is latest per
  product/retailer within 24 hours. Backend maps `product_url` to API `url`.
- `gold.price_summary.lowest_observed_price` comes from current offers (NULL if stale).
  Other price statistics cover all reviewed retailer-time observations. Row count is not date coverage.
- Current freshness and summary semantics are B's proposal to C, not a shared-contract amendment.
- Raw archive must remain complete; removing an approval retracts its Silver row on rebuild.
- Published feature branch: `codex/databricks-serpapi`, based on `main`.
  `GIT_SETUP.md` gives clone, branch-selection, Volume-upload, and notebook steps.
  Main and the existing `Iris_databrick_pipeline` branch are not modified by this feature branch.
- Raw data, `.env`, and upload archives remain local/ignored. App deployment and backend
  integration remain pending after ingestion succeeds. Push result is reported in the session handoff.

## Manual observation support (2026-11-14)
- Added a manual snapshot importer with explicit provenance, capture timestamps,
  input validation, and stable candidate IDs. Existing exact-match approval remains required.
- Local validation: `cd databricks && python3 -m unittest discover -s tests -v`:
  38 tests passed. No cloud validation of this new importer yet.
- Latest user-reported cloud counts remain 130 Bronze, 4 products, zero offers.
- Amazon evidence is pending: screenshot URL ASIN B01M0PENYV differs from the
  user-reported Product Details ASIN B0D14PTTPL. Reported model G18000, unisex-adult;
  capture approximately 2026-11-14 18:35 Chicago (2026-11-15 00:35 UTC).
  No approval or real manual snapshot has been generated from this unresolved evidence.
- Next: confirm selected variant URL, retain evidence, import and review the observation,
  then verify a populated Gold offer in Databricks.

## First manually reviewed offer prepared
- User reconfirmed the selected URL and G18000 style. Manual review uses visible Black,
  Medium, single-item selection, Amazon.com seller, stock and $10.93 price together with
  user model confirmation. ASIN discrepancy remains explicit in provenance; no ASIN
  equivalence is asserted. This supersedes the earlier pending-review status above.
- Local ignored raw file: `databricks/data/raw/manual_df2e9a19369b51861c6fbe5a5412cf32.json`.
  Approved via `config/approvals.json`; source remains `manual_snapshot`.
- Local normalization: 171 Bronze, 4 canonical products, 1 offer. These are local counts,
  not cloud counts. User's last reported cloud state remains 130 Bronze and zero offers.
- Added a reviewed product-option explanation to the B-owned app and notebook. Timing
  advice remains insufficient with one observation. Main frontend/backend unchanged.
- Upload the new manual JSON before running with the updated approval; the full raw archive is still
  required. Verify one Silver/Gold offer and the final notebook demo row.
  Cloud execution and App deployment remain unverified.

## Unified integration status (2026-11-15, on `integration/databricks-unified`)
- Both feature branches merged (Iris_databrick_pipeline first, then codex/databricks-serpapi); both original branches preserved. Merge commits PUSHED and verified: remote `integration/databricks-unified` @ `5377975ec203f1f1c859e2bba8ea8b2e869fbb33`.
- REFACTORS IMPLEMENTED (2026-11-15, code-only, NOT yet pushed — awaiting review):
  1. Insert/update-only everywhere: `sql/01_bronze.sql` MERGEs seed rows on (source, source_product_id, observed_at) — TRUNCATE removed; `sql/02_silver.sql` MERGEs on product_id / offer_id — CREATE OR REPLACE TABLE rebuilds removed; `findora_data/pipeline.py` silver MERGE lost its WHEN NOT MATCHED BY SOURCE THEN DELETE clause (revoking an approval now needs an explicit reviewed retraction, not a rebuild).
  2. Provenance scoping: seed SQL reads only `provenance LIKE 'seed-demo%'`; pipeline archive-completeness and canonical-identity checks scoped to `$.source IN ('serpapi','manual_snapshot')`, so seed rows coexist safely with real rows.
  3. Shared catalog `findora_hackathon` wired in: notebook widget default, `sql/validation.sql`, `sql/backend_queries.sql`, `app/app.yaml`, `app/app.py` fallback.
  4. Unified Gold (`sql/03_gold.sql` and `findora_data/pipeline.py::create_gold` kept in sync): `gold.product_offers` TABLE with provenance + source_type (demo/snapshot/unlabeled); `gold.price_summary` TABLE retains `lowest_observed_price` (verified-only stats); views `gold.current_offers` (24h fresh), `gold.current_price_summary` (fresh current lowest, NULL when stale), `gold.price_coverage` (distinct UTC dates + span_hours + history_status), `gold.product_catalog` (data_status: unobserved/demo/observed).
  5. DEMO HARD RULE implemented: `price_coverage` marks demo products 'demo' (never 'sufficient'); backend advice eligibility requires data_status <> 'demo' AND history_status = 'sufficient' AND a fresh verified current price; the App shows an explicit DEMO notice instead of advice availability.
  6. Gildan 4th target verified in `config/products.json` (4 targets, all with reference URLs). The ASIN discrepancy (address-bar B01M0PENYV vs reported details B0D14PTTPL) remains explicitly documented in `approvals.json` (review_method 'ASIN unresolved'); the Gildan offer is NOT treated as verified real history until product identity is confirmed — with one observation it is INSUFFICIENT_DATA for advice regardless.
- Added `tests/test_integration_contract.py`: both ingestion paths, provenance separation, insert-only safety, unified Gold contract, demo hard rule, 4-product config, ASIN documentation.
- PREFLIGHT FIXES (2026-11-15, code-only, second pass — user approved direction but no cloud execution yet):
  1. MERGE syntax: eliminated all inline `MERGE ... USING (WITH ...)` subqueries (Databricks does not guarantee CTEs inside MERGE USING). Gold MERGE sources in `sql/03_gold.sql` and `pipeline.py::create_gold` now stage in TEMP VIEWs (`_findora_gold_offers_source`, `_findora_gold_summary_source`) then MERGE USING <view>.
  2. APPROVAL REVOCATION implemented in `pipeline.py`: after the Silver MERGE, an UPDATE sets `match_type='revoked'` on any currently-exact row whose provenance `$.verification.candidate_id` is no longer in the approved set. Audit history is preserved (bronze/silver/gold rows + provenance with the original verification record stay); revoked offers are excluded from every exact-only object — current_offers, price_summary, price_coverage, advice eligibility — so they can never affect current prices or BUY/WAIT advice. Scoped to verified real rows only (seed rows carry no verification JSON, never touched).
  3. Existing Gold migration path (code-verified): `findora_hackathon.gold.product_offers` gains `provenance` via ADD COLUMN IF NOT EXISTS (NULL until the same run's MERGE backfills all 26 rows via UPDATE SET *; offer_ids are stable across the old/new Silver so every row matches); `source_type` already exists (no-op); `price_summary` schema already matches — MERGE refreshes in place. No DROP/REPLACE; rows never lost.
  4. Regression tests added: RevocationTests (marked-not-deleted, scoping, exact-only exclusion, validation audit), MergeSyntaxTests (no inline CTE in MERGE USING), IdempotencyTests (stable MERGE keys). Suite now 59/59 passing.
  5. Git hygiene verified: only the 12 intended files changed (11 M + 1 new test); root .gitignore excludes .env/.env.*; databricks/.gitignore excludes data/ (0 raw archives tracked); secret scan of the diff found only instructional text.
- STILL REQUIRING CLOUD VERIFICATION (cannot be proven without execution): ALTER TABLE ADD COLUMN IF NOT EXISTS on UC; UPDATE ... NOT IN (subquery) on Delta; MERGE USING <temp view>; MEDIAN in an aggregation source; the full insert/update flows and rerun count stability.
## Phase 1 EXECUTED against findora_hackathon (2026-11-15, commit 89028fc) — SUCCESS
- Sequence: one-time migration (ADD COLUMN provenance STRING, appended; source_type untouched) -> 01 -> 02 -> 03 -> validation. All statements OK; no SQL errors. Git tree clean throughout.
- ACTUAL counts (unchanged from before, insert/update-only confirmed): bronze.raw_offers 26, silver.canonical_products 5, silver.normalized_offers 26, gold.product_offers 26, gold.price_summary 5, gold.current_offers 15 (Nov-14 exact offers within the 24h window).
- gold.product_offers.provenance populated for ALL 26 offers (MERGE UPDATE SET * backfill by offer_id). Column order: provenance appended last (cosmetic; MERGE matches by name).
- Four Gold views created and queryable: current_offers (15), current_price_summary (5), price_coverage (5), product_catalog (5).
- Validation integrity checks all 0: invalid_offers, unlabeled_source_type, missing_provenance, orphan_offers, duplicate_offer_ids, duplicate_bronze_candidates, stale_current_offers, non_exact_in_current_offers; verified-only summary check returned 0 rows (pass). match_type: exact 25 + unverified 1 (the deliberate near-match hoodie).
- DEMO HARD RULE VERIFIED LIVE: all 5 demo products show data_status='demo', history_status='demo', advice_eligibility='not_eligible' — despite 3 distinct UTC dates spanning 312h (would otherwise be 'sufficient').
- price_summary values verified: e.g. northpeak-fp-hood-100 lowest 47.99 (Nov-14 min), median 52.99, count 5; coverage 3 retailers/product.
- Fix history this session: (1) VALUES view needed explicit 12-column alias (1dc596a); (2) ADD COLUMN IF NOT EXISTS unsupported on serverless -> migration file + information_schema guard in pipeline.py (89028fc). Local suite: 66/66.
## PHASE 3 REAL-DATA INGESTION EXECUTED (2026-11-15, commit 888bf2e) — SUCCESS with one expectation discrepancy
- Preflight: 888bf2e clean, 21 validated JSONs at volume top level, df2e9a confirmed=false, before-counts 26/5/26/26/5. Ingestion (setup + normalize + persist + review-queue write) ran first-attempt, zero pipeline errors.
- ACTUAL counts: bronze 197 = 26 demo + 171 real (carhartt 44, columbia-1533891 44, columbia-2088121 42, gildan 41); silver canonical 9 (5 demo + 4 real); silver offers 26 (all demo; 0 real); gold offers 26 (all demo); current_offers 15 (all demo).
- DISCREPANCY vs expectation: gold.price_summary = 9, NOT 5. The 4 real products each got a row with NULL lowest/median/minimum, observation_count 0, last_observed_at NULL. This is by-design MERGE behavior (summary row per canonical product; NULL when no verified offers — identical in sql/03_gold.sql and pipeline.create_gold). NO real price entered verified pricing. If 5 is required, that is a contract decision (filter unobserved rows) to make explicitly, not data damage.
- Safety verified: df2e9a (demoted Gildan) present in Bronze as candidate only; 0 real offers in Silver/Gold/current_offers/current_price_summary; product_catalog: 5 demo + 4 'unobserved' (all advice not_eligible); price_coverage 5 demo rows only; demo 26 intact in Bronze and Gold; review_queue.generated.json written with all 171 candidates.
- validation.sql: 22/22 statements OK; invalid/unlabeled/missing-provenance/orphans/duplicate-offer-ids/duplicate-bronze-candidates/stale/non-exact-in-current all 0; bronze by source: serpapi 170 (+candidate_id 170), manual_snapshot 1 (+1), demo retailers 26 (0); real-offer trace [21] returns 0 rows as expected.
- DECISION (2026-11-15, user-approved): gold.price_summary keeps one row per canonical product INCLUDING products with no verified offers — NULL price statistics, observation_count = 0. The observed 9-row behavior is the accepted contract, not a bug. Confirmed Phase 3 counts of record: bronze 197, silver canonical 9, silver normalized offers 26, gold offers 26, price summaries 9; four real products have NULL stats and zero verified offers; 26 demo observations intact; all 22 validation statements passed.

## Phase 2 IDEMPOTENCY VERIFICATION (2026-11-15, commit 89028fc, no migration rerun) — SUCCESS
- Reran 01/02/03 + validation verbatim. All statements OK, first attempt (the two mid-run Python cell crashes were a dict(Row) display bug in MY verification code, NOT SQL failures; all 22 validation statements verified clean).
- Before/after comparison, all PASS: bronze 26 (key set (source, source_product_id, observed_at) identical, 26 distinct keys for 26 rows); silver products 5 (set identical); silver offers 26 (offer_id set identical); gold offers 26 (offer_id set identical); verified-price statistics identical (price_summary tuples byte-for-byte); provenance 26/26; demo eligibility demo/demo/not_eligible for all 5 products.
- Validation integrity checks all still 0; match_type exact 25 / unverified 1; source_type demo 26; current_offers 15. No duplicates, no missing rows, no drift.

## Amazon adapter integrated locally with main (2026-11-15)
- Branch codex/amazon-integration based on main c01c991; ported only amazon_detail,
  selected-variant checks/review evidence in normalize, and six adapter tests.
- Unified persistence and main approvals unchanged; no silent restoration of the
  previously demoted Amazon approval. No warehouse start or cloud write attempted.
- `cd databricks && python3 -m unittest discover -s tests -q`: 72 passed.
- Offline replay of the saved one-request Amazon response produced candidate
  0d3fc8c37295c7f46cc376e127df89f0, USD 10.96, selected Black/M/1, Amazon.com,
  source timestamp 2026-11-15T13:42:31Z. Generic ASIN/size conflicts retained.
- Ready for code integration; review decision and live ingestion remain pending.
  See databricks/AMAZON_REFRESH.md. No new SerpAPI quota used in this step.

## Amazon selected-variant review completed locally
- Integrated latest main aece95a into this isolated branch (backend included).
- New candidate 0d3fc8c37295c7f46cc376e127df89f0 reviewed against the saved provider
  response: selected Black/Medium/1 with matching selected ASIN; G18000; single-offer
  Amazon.com stock/price USD 10.96. Accepted explicit selections over generic details
  conflicts, recording rationale and acknowledgement. No parent/child ASIN claim.
- Existing manual Amazon candidate remains disabled; Columbia approval unchanged.
- Local real-response normalization produces one reviewed offer; duplicate replay
  preserves one offer. This is not a live cloud ingestion or full-archive validation.
- Registry regression test now verifies separate old-disabled/new-reviewed records
  and preserved conflict evidence instead of assuming one Gildan observation forever.
- Upload the new response alongside the complete cloud archive before ingestion.
  Main remains the existing baseline; no warehouse request or new API spend here.
