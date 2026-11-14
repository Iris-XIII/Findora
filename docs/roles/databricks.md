# Databricks — role-specific instructions

**Owner:** Data pipeline and deployed Databricks App owner

**Write scope:** `databricks/**` and `docs/progress/databricks.md`.

## Deliverables
Configure workspace, ingest sourced records, Bronze/Silver/Gold transformations, provenance, SQL views, deployment and judging preflight.

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
