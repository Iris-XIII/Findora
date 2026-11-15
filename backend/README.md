# Findora backend handoff

Branch: `codex/backend-databricks`, based on main `6599466`.
The app is read-only. No ingestion, approvals, or Gold migrations run here.

## Start

Install `requirements.txt` in a Python environment. From `backend/`:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Default mode is `demo` with explicitly illustrative scaffold data. For Gold, configure
these environment variables privately before starting (no automatic .env loading):

```text
FINDORA_DATA_MODE=databricks
FINDORA_CATALOG=findora_hackathon
DATABRICKS_HOST=https://dbc-84be3fa6-3f68.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse-id>
FINDORA_CORS_ORIGINS=http://localhost:5173,https://<your-frontend-host>
```

Use Databricks SDK unified authentication: a privately supplied DATABRICKS_TOKEN
where supported, or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET for a service
principal, or an existing authenticated SDK profile. Do not send credentials to
frontend JavaScript or commit them. The identity needs warehouse CAN USE plus
USE CATALOG, USE SCHEMA, and SELECT on the Gold objects. Obtain the HTTP Path from
SQL Warehouses → your warehouse → Connection details. No SQL warehouse has yet
been tested from this checkout.

Authentication reference: https://docs.databricks.com/aws/en/dev-tools/python-sql-connector

## HTTP contract

Local base: `http://localhost:8000`. Deployment URL is pending. Interactive schema:
`/docs`; machine-readable schema: `/openapi.json`. No frontend response shape changes.

| GET route | Parameters | Result |
|---|---|---|
| `/health` | none | status, data_mode; Gold query failure returns 503 |
| `/products/search` | `q` optional, max 200 characters | items, max 50; empty q lists catalog |
| `/products/{id}` | canonical product id | product or 404 |
| `/products/{id}/offers` | canonical product id | fresh reviewed offers, price ascending |
| `/products/{id}/history` | canonical product id | eligible observed points and data_status |
| `/products/{id}/advice` | canonical product id | decision, explanation, evidence including date coverage |
| `/products/{id}/similar` | canonical product id | up to 2 same-category alternatives; unavailable price is null |

Example paths for frontend testing:
`/products/search?q=Gildan`, `/products/gildan-18000-unisex-black-m-single/offers`.
Do not assume that Gildan has a current approved offer: approval state differs between
branches. Test the actual Gold results. Columbia id: `columbia-2088121-black-m-regular`.

Illustrative empty-offer response (not a claim about live Gold):

```json
{"product_id":"gildan-18000-unisex-black-m-single","offers":[]}
```

Illustrative missing-history response:

```json
{"product_id":"gildan-18000-unisex-black-m-single","observations":[],"data_status":"insufficient"}
```

Generate complete examples against your configured warehouse:

```bash
curl -fsS http://localhost:8000/health
curl -fsS 'http://localhost:8000/products/search?q=Gildan'
curl -fsS http://localhost:8000/products/gildan-18000-unisex-black-m-single/offers
curl -fsS http://localhost:8000/products/gildan-18000-unisex-black-m-single/history
curl -fsS http://localhost:8000/products/gildan-18000-unisex-black-m-single/advice
```

## Pricing and advice rules

Gold catalog `unobserved` maps to API `insufficient`. A Gold-connected health result
uses `data_mode=observed` to indicate the adapter, not that every product has real data.
Each product/offer retains its own demo/real classification. Unknown or revoked offers
never enter real pricing. Demo products only return labeled demo offers; real products
exclude demo observations. Future, non-finite, non-USD and nonpositive prices are excluded.
Current offers are latest per retailer within the last 24 hours. History retains older
eligible observations. SQL sessions and coverage dates use UTC.

A NULL summary is not zero. Advice computes statistics from filtered Gold observations,
not placeholder price_summary rows. No current offer, no history, demo data, fewer than
3 distinct UTC dates, or less than 48 hours span => INSUFFICIENT_DATA. Otherwise current
price <= 90% of historical median => BUY; else WAIT_OR_COMPARE. This is a transparent
heuristic, not a predictive model. Coverage is included in advice.evidence; the existing
history response shape is unchanged. Similarity is category/brand based, not fit advice.

No silent fallback to demo on warehouse failures: return generic HTTP 503. No credentials
or connector error details reach clients. Queries bind user inputs. The current small-demo
implementation fetches eligible history per product without pagination; revisit for scale.

## Validation

```bash
python -m pytest tests -q
```

Tests use synthetic fixtures. Live smoke checks require configured private credentials.
Before integration, check known-product and missing-product routes, source labels, NULL
prices, freshness, and insufficient-history responses against actual Gold. A deployed API
and verified live endpoint responses are still required for final frontend handoff.

Complete route examples generated with synthetic test inputs are in
`examples/synthetic_responses.json`. They illustrate JSON shapes only, not live pricing.
Local validation: 31 tests pass. Live warehouse verification: pending connection setup.
