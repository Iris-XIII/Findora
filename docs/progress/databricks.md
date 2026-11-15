# Databricks progress

**Status:** IN PROGRESS
**Last updated:** 2026-11-14

## Local verification evidence
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

## Handoff notes
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
- Upload the new manual JSON before running with the updated approval; the full raw
  archive is still required. Verify one Silver/Gold offer and the final notebook demo row.
  Cloud execution and App deployment remain unverified.

## User-reported cloud success and integration review (2026-11-14 Chicago)
- User supplied successful notebook output in catalog `workspace`: Bronze 171,
  canonical products 4, Silver normalized offers 1, Gold product_offers 1,
  current_offers 1, price_summary 1. Final notebook row shows Gildan Black M single,
  Amazon.com USD 10.93 at 2026-11-15T00:35:00Z and insufficient timing history.
  This supersedes the earlier cloud-unverified ingestion status; app deployment and
  backend integration remain unverified. Evidence is user-provided output, not an
  independently executed cloud check. Rerun idempotency remains to be verified.
- Upload issue resolved: 10 missing raw files were copied from the Volume root into
  its `responses` directory without deleting originals. Diagnostic cells are temporary.
- Fetched `origin/integration/databricks-unified` at e1aac7a. It already contains
  d1d2a49 (our latest implementation); no duplicate code push is needed.
- Deployment differences need resolution before running integration against the
  working workspace: default catalog changes from workspace to findora_hackathon;
  Gold product_offers and price_summary change from views to Delta tables. The
  integration code's CREATE TABLE IF NOT EXISTS / ALTER TABLE / MERGE sequence is
  not a migration of our existing views. Do not blindly run it against those views.
- Recommended next milestone: prepare/test the integration migration and confirm
  backend catalog, then verify the one real Gold offer reaches the demo. Collect
  further real dated observations afterward; do not substitute seed history for
  measured history or promise forecasting from one price point.

## Google Product detail lookup added (2026-11-15)
- `findora_data.collect` now supports `--product-lookups N` (default 0, opt-in): per
  product, up to N `engine=google_product` SerpAPI calls, preferring provider product
  IDs from `google_shopping` discovery (deduplicated, query fallback when absent).
  The request budget still reserves one discovery call per remaining target, and the
  dry-run ceiling formula includes the lookups. Default behavior is unchanged.
- `findora_data.normalize` accepts `google_product` envelopes: store rows parse like
  `google_immersive_product` (retailer from `name`, same price/currency/URL checks),
  land in Bronze + review queue only, and the looked-up Google product ID is recorded
  in provenance as `lookup_product_id`. No auto-exact matching was added; existing
  variant/price/merchant approval requirements apply unchanged.
- Motivation: find a second reviewable exact offer for the focused Gildan G18000
  Black adult M target, alongside the manually reviewed Amazon snapshot.
- Local validation: `python3 -m unittest discover -s tests -v` — 43 tests passed
  (5 new: google_product parsing/review-only/approval; collector id preference,
  budget reservation, query fallback). `collect --products config/focus_products.json
  --dry-run` — 1 target, ceiling 3; with `--product-lookups 1` — ceiling 4.
- PriceHistory.app integration deliberately deferred: no verified public API; any
  future use must be labeled imported third-party history and cannot independently
  verify current stock or selected-variant price.
- Next: run the focused collection with a real key (not available in this
  environment), upload new responses to the existing Volume, re-run ingestion, and
  review the new `google_product` candidates for a second exact offer. Cloud counts,
  offer approvals, and App deployment remain unverified.

## First live google_product collection (2026-11-15)
- User created the private `databricks/.env` in the workspace copy (gitignored;
  packaging exclusion tests still pass). Key verified working via one live
  `google_shopping` diagnostic call.
- Two full focused runs failed only on the google_product step: calling with
  `product_id` returned HTTP 200 with SerpAPI error `Google Product hasn't returned
  any results for this query.` Discovery + both immersive detail calls succeeded
  and were saved (3 requests each run; batches `603c08b9...` and `e1972f6a...`).
- Fix: the collector now prefers the provider's own prebuilt `serpapi_product_api`
  link token (`page_token` param; embedded api_key never copied into request
  params), falls back to product ID, then the query. Rows whose title mentions the
  target color and size are tried first — ordering heuristic only. 44 tests pass
  locally (one new: prebuilt-token preference, variant-title ordering, no key
  propagation).
- Hybrid rerun (replayed saved discovery, no repeat charge; 1 paid lookup) saved a
  successful `google_product` envelope. Lookup targeted `18000 Gildan - Heavy Blend
  Crewneck Sweatshirt | Black | Size M by Screen Print Outlet` ($18.64, one store
  row, Google `/goto` redirect link).
- Local review queue (workspace `data/raw` only; this is NOT the full archive — the
  original 11 responses and manual snapshot remain in the user's local raw dir and
  the Volume): 46 candidates, including the Screen Print Outlet `/goto` candidate
  (`merchant_redirect_requires_resolution`) as the reviewable second offer path.
- Approximate SerpAPI spend this session: ~9 searches (6 successful run requests,
  1 diagnostic shopping success, 2 error/failed responses likely uncharged).
- Next: resolve the Screen Print Outlet `/goto` link per README section 2, verify
  Black/M/single-unit/$18.64 on the merchant page, then approve for a second exact
  offer. Upload the new raw envelopes into the existing Volume `responses` directory
  and rerun ingestion. Cloud rerun and App deployment remain unverified.

## Amazon price typo corrected (2026-11-15)
- User identified that the approved manual snapshot's USD 10.93 was a transcription
  typo; the observed Amazon price was USD 10.95 (reconfirmed on the live page).
  No price change occurred — it is the same single 2026-11-15T00:35Z observation.
- Correction method (no silent edits): reconstructed the exact original observation
  by matching candidate-id hash df2e9a19... (Amazon.com, /dp/B01M0PENYV?th=1&psc=1,
  observed 00:35Z), created corrected manual snapshot candidate c7c485f5... at USD 10.95
  with a documented correction chain in provenance, and replaced the approval entry.
  The erroneous 10.93 raw envelope remains in the archive unapproved (Bronze only).
- Staged 9 new envelopes into the Volume `responses` directory (30 files total):
  two focused SerpAPI batches (discovery + immersive details), the hybrid replay
  batch with the google_product Screen Print Outlet lookup, and the corrected manual
  snapshot.
- Cloud rebuild executed from this session (notebook 01_ingest, catalog workspace):
  Bronze 218, canonical products 4, Silver offers 1 — Amazon.com USD 10.95 exact at
  2026-11-15T00:35Z; gold.current_offers/price_summary 1 row (lowest/median/min
  10.95, observation_count 1); price_coverage 1 distinct date. Idempotent rerun
  produced identical counts. The Gold offer provenance carries the full correction
  chain (original_transcribed_price 10.93, price_correction_of df2e9a19...).
- Screen Print Outlet google_product candidates (incl. the /goto redirect row) are
  now in the cloud review queue, unapproved. History remains 1 of >= 3 observations.
- Repo copies of `config/approvals.json` and the new code/tests/docs changes in this
  Git checkout are uncommitted; commit/push needed to reach the user's local clone.

## Retailer-specific probe (isolated codex/retailer-discovery branch)
- Based on remote discovery branch a410a83; original checkout and uncommitted
  Google-ranking edits preserved. Reused ranking module/focus rules in isolated branch.
- Implemented two-request Amazon/Walmart probe; report and raw responses stay in
  ignored data/retailer_probe, outside ingestion inputs. No approval or table changes.
- Live run with privately configured key: 60 Amazon + 14 Walmart organic results.
  Batch 7be16afec5cd4f99b0304c0de5341d43; exactly two requests, no retries/detail calls.
- Search returns brand/model/variant leads, but no new verified Black/M/single offer.
  Alternate variant links must not inherit a parent search price. Marketplace seller
  identity remains separate (e.g. Walmart marketplace vs JustBlanks).
- Fallback retained: existing reviewed data. No new prices approved, no Databricks
  quota consumed, no claim of automatic verification or historical forecasting.
- Local suite: 50 tests passed. CLI dry run confirmed two-request ceiling.

## Targeted Amazon result (2026-11-15)
- One user-authorized amazon_product lookup for B01M0PENYV succeeded; observation
  2026-11-15 13:42:31 UTC. Selected Black / Medium / Number of Items 1;
  product and single purchase offer USD 10.96; In Stock; shipper/seller Amazon.com.
- Response reproduces details ASIN B0D14PTTPL vs selected ASIN B01M0PENYV;
  generic special_size=large also conflicts with selected Size=Medium. Retain
  both discrepancies rather than claim fully consistent identifiers/metadata.
- Raw and comparison files saved under ignored data/retailer_probe, documented in
  RETAILER_PROBE.md. No approval changes, no historical price overwrite, no cloud
  ingestion, and no new normalization code in this step. Evidence lookup tested live.

## Amazon detail adapter prepared (2026-11-15)
- Added amazon_detail CLI for offline saved-response import or one-request ASIN refresh.
  Normalizer preserves source timestamp, selected variants, marketplace seller, stock,
  and contradictory metadata. Exact-target mismatch blocks approval; source conflicts
  require explicit reviewer acknowledgement. Existing approval file untouched.
- Offline conversion of the previously fetched response produced standard ingestion
  envelope amazon_0d3fc8c37295c7f46cc376e127df89f0.json under ignored data/amazon_refresh.
  One candidate, zero approved offers; no API request or cloud action in this step.
- Validation: `cd databricks && python3 -m unittest discover -s tests -q`: 56 passed.
- Integrate adapter code into latest unified main before cloud ingestion. Do not deploy
  this discovery branch's older pipeline/approval state wholesale. Tests are local;
  cloud persistence and backend visibility for the new candidate remain pending.
