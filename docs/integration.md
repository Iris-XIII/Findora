# Integration board

Use `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `VERIFIED` only. VERIFIED requires evidence (command or screenshot and commit).

| Integration | Owners | Status | Verification |
|---|---|---|---|
| Frontend → mock FastAPI | A + C | NOT STARTED | search in browser |
| Bronze → Silver → Gold | B | NOT STARTED | SQL counts and sample rows |
| FastAPI → Databricks Gold | B + C | NOT STARTED | `/health` observed + offers query |
| Exact matching | B + C | NOT STARTED | variant-safe sample |
| Similar product API | C | NOT STARTED | two distinct alternatives |
| Price history and advice | B + C | NOT STARTED | observed timestamps and coverage |
| Deployed Databricks App | B | NOT STARTED | accessible URL + live Gold query |
| End-to-end judge flow | A + B + C | NOT STARTED | search → offers → history → alternatives |

## Integration checkpoints
- H3: mock UI and API communicate.
- H8: at least one query from Gold flows through FastAPI.
- H14: core features work on same product ID.
- H19: Databricks App live.
- H22: final end-to-end demo rehearsed.
