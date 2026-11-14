# Backend — role-specific instructions

**Owner:** FastAPI and recommendation intelligence owner

**Write scope:** `backend/**` and `docs/progress/backend.md`.

## Deliverables
Implement API contracts, Databricks adapter, exact-product matching validation, similarity scoring, evidence-based buy/wait and tests.

## First three steps
1. Read shared contracts and confirm sample `product_id`.
2. Build smallest working slice using mock or seeded data.
3. Test and update progress with exact evidence; coordinate integration.

## Integration handoff
- Frontend consumes only documented FastAPI JSON; show missing-data states.
- Databricks provides exact Gold object names, query results, source metadata and deployed App URL.
- Backend maintains stable HTTP response shapes and switches from demo to observed mode only after verifying Databricks results.

## Agent reminder
Do not modify another role's files without agreement. Do not claim completion based solely on generated code.
