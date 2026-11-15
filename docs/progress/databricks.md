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
