# Findora — Overall design document

## 1. Product statement
**Findora** helps people discover what's worth buying, **where** to buy it, and **when** to buy. Theme: **Let's Dig In** — dig beneath the sticker price.

**Demo story:** search a specific product → compare exact-item retailer offers → inspect observed price history and a transparent buy/wait signal → discover genuinely similar alternatives → save the product.

## 2. Goals and boundaries
**P0**: Product search/detail, exact-product price comparison, similar-product suggestions, observed price history + evidence-based buy/wait signal, Bronze→Silver→Gold Databricks data spine, deployed Databricks App, integrated frontend/backend.
**P1**: Saved-product collection, basic budget arithmetic, more supported retailers.
**P2**: Statistical forecasting only with adequate real history, advanced semantic/image similarity, fit/review analysis, Chrome extension.

Do not promise comprehensive internet-wide search, reliable future price predictions, or automatic purchasing. No unsupported all-time-low claims. Support a narrow, well-tested product subset.

## 3. Architecture
```text
[React/Vite web app] --HTTP JSON--> [FastAPI]
                                         |
                              [Databricks SQL connector]
                                         |
                   [Gold served views / Silver canonical / Bronze raw]
                                         ^
                   [Authorized feeds / datasets / imported snapshots]

[Databricks App] --queries--> [Gold served views]
```

Frontend does not connect directly to Databricks or hold Databricks credentials. FastAPI provides stable contracts; Databricks owns persistent price intelligence. Initially, a deterministic demo-data adapter allows independent frontend work. Replace it with a Databricks adapter once verified. A minimal Databricks App may be a small Streamlit or other supported app with product lookup and SQL-backed offer/history output; deployment and permissions must be tested in the actual workspace.

## 4. Databricks track requirements (from team-provided slides)
- Databricks must be **core** to the project.
- Real data spine: **raw → cleaned → served**, even if small.
- Live experience: **deployed Databricks App or Genie space** judges can try.
- Creativity and impact matter.
- Free Edition tip on slide: Apps stop 24 hours after deployment; redeploy/check Sunday morning before 2 PM judging.
- Compute daily quotas: keep data small; skip heavy training.

**Proof package**: three table/view screenshots or SQL queries showing record flow, an app URL, a real end-to-end search from served Gold data, and an explanation of data provenance.

## 5. Core feature design
### Exact price matching
Normalize brand, model/SKU, variant, size/color, currency. Only label two offers as the **same product** when evidence is sufficient; otherwise list them as similar products. Show observed timestamp and source link. Cheapest means lowest verified listed price among available observed offers, not the whole internet or necessarily final landed cost.

### Similar products
MVP: rank by category, brand/model features, normalized tokens, price band, and optional precomputed text embeddings. Exclude exact matches; show why an alternative is similar. Do not require GPU training.

### Price tracking and buy/wait
Use observed history with timestamps and provenance. Compute min/median/current and recent movement. Return `INSUFFICIENT_DATA` if fewer than 3 distinct dated observations or insufficient span; never imply future forecasts are measured facts. Optional heuristic `BUY` if current price is materially below median, otherwise `WAIT_OR_COMPARE`; these are suggestions, not guaranteed future outcomes.

### Saved items
Local browser storage initially; backend persistence is optional P1. Saving does not mean purchased. Budget arithmetic is deterministic.

## 6. Data model
- `raw_offers`: source, source_product_id, title, brand, variant, price, currency, url, observed_at, ingestion_batch.
- `canonical_products`: product_id, title, brand, category, model, image_url, attributes_json.
- `normalized_offers`: offer_id, product_id, retailer, price, currency, url, observed_at, match_confidence.
- `price_history`: product_id, retailer, price, currency, observed_at, provenance.
- `gold_product_summary`: product_id, current_lowest_price, median_observed_price, minimum_observed_price, observation_count, last_observed_at.

Use Delta tables for Bronze/Silver and Gold views/tables. Names are proposals; see `docs/data-contract.md` for agreed interface. Product IDs are strings, stable across layers. Price currency is explicit. Use UTC ISO-8601 timestamps in API.

## 7. Integration and acceptance criteria
1. Frontend searches and opens one supported product via FastAPI.
2. FastAPI obtains at least one real, documented Gold query result from Databricks.
3. Comparison shows multiple offers for at least one **verified exact item**, or honestly shows insufficient coverage.
4. History displays only observed points and their source/date; any seeded data clearly labeled.
5. Similar alternatives show at least two nonidentical products, with simple similarity rationale.
6. Databricks App is live, uses Gold data, and is independently testable by judges.
7. Team can trace a displayed value to raw input, normalized record, and served result.

## 8. 24-hour milestones
| Hours | Data engineer | Backend/intelligence | Frontend |
|---|---|---|---|
| 0–3 | workspace, seed, Bronze | FastAPI mock routes, schema | React shell, cards |
| 3–8 | Silver/Gold, SQL query | Databricks adapter, search/offers | wire search/detail |
| 8–14 | price stats, provenance | similarity, buy/wait | charts, comparisons |
| 14–19 | deploy Databricks App | integrated tests | polish and responsive UI |
| 19–24 | verify live app, evidence | fix bugs, demo fallbacks | demo rehearsal |

**Stop rule:** If a core Databricks query is not working by hour 8, reduce product coverage, not platform proof. If live price sources fail, use documented real snapshots and label them; do not manufacture history.

## 9. Risks and mitigations
- No legitimate historical dataset: show observed snapshots and insufficient-data state, not fake forecasting.
- Retailer anti-bot/data access: use authorized APIs, public datasets, or manually documented snapshots; narrow coverage.
- Different variants matched incorrectly: require model/variant verification, otherwise classify as similar.
- Free Edition compute/app availability: preflight credentials, quota, deployment, and app URL; retain backup demo recording.
- Cross-role API drift: single shared contract, mock fixtures, smoke test, frequent merge checkpoints.
- Secret leakage: `.env` ignored; least-privilege workspace access; server-only credentials.

## 10. Judge pitch
“Findora digs through fragmented retailer offers and historical price observations to show what is worth buying, where, and when. Databricks turns raw shopping records into cleaned, canonical products and served price intelligence that powers our live app.”

## 11. Open decisions (resolve in first 30 minutes)
- Which 1–2 categories and 3–5 demo products? --> clothing
- Which authorized product/price source and which historical dataset?
- Which team member owns Databricks App deployment and credentials?
- Is the Databricks App the main judge demo or a companion to the React app?
- Which exact product ID conventions and source/provenance fields?
