# Findora agent collaboration rules

You are working on a 24-hour, 3-person hackathon. Optimize for a working, verifiable demo.

## Required reading at session start
- `docs/design.md`
- `docs/api-contract.md`
- `docs/data-contract.md`
- `docs/integration.md`
- `docs/roles/<your-role>.md`
- `docs/progress/<your-role>.md`

## Ownership
- Frontend: `frontend/**`, `docs/progress/frontend.md`
- Databricks: `databricks/**`, `docs/progress/databricks.md`
- Backend: `backend/**`, `docs/progress/backend.md`
- Shared docs and contracts: change only after explicit teammate agreement, record decision in `docs/decisions.md`.

## Non-negotiables
1. Do not claim untested features are done. Use VERIFIED only after a reproducible test.
2. Preserve API response shapes and canonical `product_id` across all layers.
3. No invented historical prices, retailers, forecasts, source URLs, or review evidence. Label seed/demo data.
4. Do not commit secrets, API keys, credentials, private user data, or `.env`.
5. Avoid introducing unnecessary infrastructure, scraping dependencies, heavy model training, or new services.
6. Make focused changes in your owned directory. Propose cross-role changes first.
7. Update your progress file with what changed, commands/tests and result, blockers, and next step.
8. Integrate early. Favor a working vertical slice over isolated feature completeness.
9. Do not assume Markdown progress files are automatically synchronized. Pull the latest Git branch and reread docs.
10. When uncertain, report assumptions and ask the teammate; never silently alter contracts.

## Agent startup prompt
Read AGENTS.md, docs/design.md, docs/api-contract.md, docs/data-contract.md, docs/integration.md, docs/roles/<role>.md, and docs/progress/<role>.md. State current verified facts, unresolved dependencies, and next smallest task. Do not change shared contracts without approval.

## Agent handoff prompt
Summarize modified files, commands/tests and outcomes, integration dependencies, and blockers. Update only docs/progress/<role>.md. Do not mark anything VERIFIED unless tested.
