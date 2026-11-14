# Findora 💎 — Discover what's worth buying, where, and when

24-hour hackathon MVP · 3 contributors · Databricks track

## Start here
1. Read [`AGENTS.md`](AGENTS.md) and [`docs/design.md`](docs/design.md).
2. Choose your role: [`frontend`](docs/roles/frontend.md), [`databricks`](docs/roles/databricks.md), or [`backend`](docs/roles/backend.md).
3. Agree on [`docs/api-contract.md`](docs/api-contract.md) and [`docs/data-contract.md`](docs/data-contract.md) before implementing.
4. Run the mock FastAPI service and frontend locally; replace mock data incrementally with Databricks-backed results.
5. Update only your role's progress file, and coordinate changes to shared contracts.

## Local quickstart
Requires Python 3.11+ and Node 20+.

```bash
# terminal 1
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and API docs at http://localhost:8000/docs.

The initial application uses **explicitly labeled demo data**. No retailer prices or forecasts are verified live until the Databricks integration is complete.

## Databricks track
Judging slide supplied by the team: Databricks must be core; demonstrate raw → cleaned → served data; provide a live Databricks App or Genie space; show creativity and impact. Free Edition Apps may stop after 24 hours and compute quotas apply. Redeploy/check the morning of judging.

## Definition of MVP
A user searches a supported product, sees canonical product details, verified retailer offers, observed price history, similar alternatives, and a data-supported buy/wait explanation. A Databricks App exposes the same served intelligence and is demonstrably backed by Bronze/Silver/Gold tables.
