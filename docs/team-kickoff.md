# First 30 minutes — kickoff checklist

- [ ] All three accept GitHub invite and clone repository.
- [ ] Assign names to A (frontend), B (Databricks), C (backend).
- [ ] Choose 3–5 products and documented sources, including any legitimate historical data.
- [ ] Confirm product ID conventions and API schema; record deviations in `docs/decisions.md`.
- [ ] Create branches `feat/frontend`, `feat/databricks`, `feat/backend`.
- [ ] Test frontend dev server and FastAPI `/health`.
- [ ] B confirms Databricks SQL warehouse and Apps access.
- [ ] Schedule 3h, 8h, 14h, 19h, 22h integration checkpoints.

## Git commands
```bash
git clone <your-repository-url>
cd findora
git checkout -b feat/backend  # choose your own role
# after edits:
git add backend docs/progress/backend.md
git commit -m "feat(backend): add product search adapter"
git push -u origin feat/backend
```

Protect `main` with PR review if practical. During the hackathon, use short-lived branches and merge frequently after smoke tests. Never have all three agents rewrite shared files concurrently.
