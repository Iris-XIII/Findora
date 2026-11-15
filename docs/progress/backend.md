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
