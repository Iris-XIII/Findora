# Backend progress

**Status:** IN PROGRESS
**Branch:** codex/backend-databricks, isolated worktree based on main 6599466

## Implemented
- Explicit demo/Databricks adapter selection; SDK unified authentication and bound SQL
  parameters against configurable catalog (default findora_hackathon.gold).
- Product search/catalog/detail, fresh current offers, eligible historical observations,
  category-based alternatives, and BUY/WAIT_OR_COMPARE/INSUFFICIENT_DATA endpoints.
- Preserved existing response shapes. Coverage is in advice.evidence. Gold unobserved
  maps to API insufficient. SQL and application filters exclude revoked/unverified,
  future, non-finite, nonpositive, non-USD and wrong-source prices. 24h freshness enforced.
- Demo never yields buying advice. Zero observations retain null prices and insufficient
  advice; summary placeholders never feed the heuristic. No forecast model is claimed.
- Configurable CORS; connection failures return generic 503, no silent demo fallback.
- backend/README.md supplies setup, endpoint URLs, query parameters and live smoke commands.
  backend/examples/synthetic_responses.json supplies explicitly synthetic response examples.

## VERIFIED locally
- `cd backend && PYTHONPATH=/tmp/findora_backend_deps:. python3 -m pytest tests -q`:
  31 passed (one third-party TestClient deprecation warning).
- Dependencies installed under /tmp because system Python has neither pip nor ensurepip.
  No system Python packages modified. All tests use synthetic fixtures/fake stores;
  these results do not verify Databricks SQL syntax, credentials or warehouse permissions.

## Pending / blockers
- User needs SQL Warehouse Connection details → HTTP Path and privately configured
  SDK credentials. Asked for nonsecret HTTP Path; tokens must not be pasted in chat.
- Live endpoint testing against actual Gold and deployment URL remain unverified.
- Main and discovery branch have divergent Amazon approvals; adapter reads actual Gold
  and never promotes a Git approval by itself. No ingestion/config approvals changed here.
- Review history SQL performance before growing beyond small hackathon datasets.
- Frontend can develop against existing demo mode or the documented fixture shapes,
  but only claim Gold integration after live smoke tests succeed.
- Original worktree and its unfinished SerpAPI edits remain untouched.

## Main integration — 2026-11-15 (supersedes earlier setup status)
- Fetched origin/main c01c991 (frontend API integration and Discover UI) and merged
  into codex/backend-databricks cleanly. Backend code retained, no conflicts, no
  frontend edits. Original SerpAPI checkout/worktree left untouched.
- Main's frontend expects our existing route/evidence shapes and falls back from
  absent /discover (404) to /products/search. The proposed /discover contract is
  not implemented or silently approved by this integration.
- Default local CORS now supports localhost:5173 and 127.0.0.1:5173. Deployed
  frontend origin must be configured explicitly through FINDORA_CORS_ORIGINS.
- VERIFIED: PYTHONPATH=/tmp/findora_backend_deps:backend python3 -m pytest backend/tests -q:
  37 passed; one third-party TestClient deprecation warning. git diff --check passed.
  Tests include local/custom CORS, foreign-origin denial, discovery 404 fallback,
  all frontend-consumed routes, empty catalog query, 404/422 errors, plus pricing guards.
- Node/npm unavailable; frontend browser/build tests not rerun. These are backend
  integration tests, not a claim of end-to-end browser or live warehouse verification.
- CLI installed at ~/.local/bin/databricks and findora profile authenticated in prior
  session. HTTP Path known: /sql/1.0/warehouses/00869224988d7681. Auth setup is no longer
  the blocker. Earlier daily Free Edition quota prevented warehouse startup. Current
  read-only status check: STOPPED; no start request made during this integration.
- Remaining: live Gold smoke check and deployed backend URL, then frontend live test.
  No change to 24-hour freshness policy, approved observations, or cloud tables.

## Offer guidance and Columbia demo check — 2026-11-15
- One fresh verified offer now gets actionable retailer/price guidance while retaining
  INSUFFICIENT_DATA in the API for unavailable buy/wait timing. No invented history.
- Search accepts the explicit spelling alias columina -> columbia, preserving other tokens.
- VERIFIED: 42 backend tests pass, including one-observation guidance and bound alias query.
- Live SQL verified Columbia 2088121 Black/M Regular in Gold current_offers: $220,
  Columbia Sportswear, exact snapshot at 2026-11-15T03:09Z. Columbia 1533891 has no offer.
- Cloud data unchanged; deploying branch UI/backend changes remains an integration step.

## On-demand product discovery — isolated proposed backend change (2026-11-15)
- Added server-side `/discover?q=` for arbitrary clothing keywords or pasted product URLs.
  URL input is parsed for search terms; arbitrary pages are never fetched.
- SerpApi candidates are always unverified, separate from existing Gold/approved offers.
  Curated catalog matches and same-category suggestions are returned even when SerpApi
  credentials are not configured; no synthetic retail prices added.
- Existing `frontend/index.html` already supports the `/discover` response and API-mode
  UI. No frontend source files or shared API contracts changed in this patch.
- Uses only server-side `SERPAPI_API_KEY`; 20-request/hour process-local cap and
  10-minute caching reduce accidental repeated charges. No live API calls made in tests.
- Tests use fake provider data. Live SerpApi access, Databricks permissions, and
  deployed end-to-end behavior remain unverified.
- Integration note: backend owner should review new endpoint, key deployment and
  budget policy before merging; shared contracts can be updated by agreement.

## Discovery patch inspected and integrated — 2026-11-15
- Updated codex/amazon-integration with main cfc68ea before applying the supplied patch.
- Patch applies cleanly. ZIP is not equivalent to the patch: it additionally changes
  collectors/normalization and would re-enable the held Amazon approval. Those changes
  were not imported. Current main's hold and all frontend files are preserved.
- Verified frontend renderDiscovery/snapshotFromCandidate accepts endpoint fields;
  deployment packaging copies backend/app/*.py, including the new discovery module.
- Fixed malformed URL/provider result handling, expired-cache pruning/256-entry cap,
  serialized concurrent requests, cached/budget-exhausted statuses, currency/hostname
  boundaries, and preservation of the Columbia spelling alias.
- VERIFIED: 56 backend tests plus 16 deployment diagnostics tests passed (72 total),
  using synthetic providers only; no paid requests or cloud writes.
- Existing frontend untouched; Node/npm unavailable here, so no new browser/build run.
- Runtime needs SERPAPI_API_KEY in the app environment. User reports key configured;
  no secret contents inspected or logged. Live provider/app deployment not verified.
