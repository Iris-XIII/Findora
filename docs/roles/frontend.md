# Frontend — role-specific instructions

**Owner:** React/Vite interface owner

**Write scope:** `frontend/**` and `docs/progress/frontend.md`.

## Deliverables
Search page, product details, retailer offers, price history chart, similar product cards, clear demo/observed labels; integrate API; responsive demo.

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
