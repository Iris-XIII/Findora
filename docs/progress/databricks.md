# Databricks progress

**Status:** IN PROGRESS — Bronze/Silver/Gold seed slice VERIFIED; real data sources + backend integration + App deployment pending
**Last updated:** 2026-11-14 (branch `Iris_databrick_pipeline`)

## Verified completed

### Unity Catalog namespace (as proposed in docs/data-contract.md)
- Catalog `findora_hackathon` with schemas `bronze`, `silver`, `gold` — created and confirmed via `information_schema.schemata`.

### Pipeline scripts (databricks/sql/, run in order)
- `01_bronze.sql` — `bronze.raw_offers` DDL per data contract + 26 labeled seed-demo rows (5 clothing products, 6 fictional retailers, 3 dated observations per product, all `provenance` = `seed-demo: ...`, URLs are example.com placeholders).
- `02_silver.sql` — `silver.canonical_products` (5 rows) and `silver.normalized_offers` (26 rows) rebuilt from Bronze. `product_id` = `lower(brand)-lower(model-normalized)` e.g. `northpeak-fp-hood-100`. `match_type='exact'` only when raw variant equals canonical variant (mode per product); otherwise `unverified`.
- `03_gold.sql` — `gold.product_offers` (26 rows; price>0, USD-only filter, dedup, `source_type='demo'` from seed provenance) and `gold.price_summary` (5 rows, **verified (exact-match) offers only** per design.md "cheapest means lowest verified listed price"; products with no verified offers would appear with NULL stats and `observation_count=0`).

### Validation evidence (run on serverless SQL, 2026-11-14)
- Row counts: bronze.raw_offers=26, silver.canonical_products=5, silver.normalized_offers=26, gold.product_offers=26, gold.price_summary=5.
- `product_id` consistency: 0 canonical IDs missing from gold.product_offers / gold.price_summary; 0 silver offer IDs missing from canonical. No cross-layer drift.
- Seed labeling: 0 bronze rows without `seed-demo` provenance; 0 gold rows with `source_type <> 'demo'`. Unverified offers preserved: 1 (MegaMart hoodie size-M near-match, `match_type='unverified'`, kept in gold.product_offers, excluded from price_summary).
- Trace (bronze -> silver -> gold): Campus Apparel hoodie offer 47.99 @ 2026-11-14T12:00:00Z appears identically in all three layers; gold.price_summary lowest for `northpeak-fp-hood-100` = 47.99.
- `databricks/sql/validation.sql` executed: all counts returned as above; note its `lowest_price` column is a raw MIN over all offers incl. unverified (44.99 for the hoodie) — the verified statistic is `gold.price_summary.lowest_observed_price` (47.99).
- Verified-only aggregation correction to `gold.price_summary` explicitly approved by teammate 2026-11-14: unverified offers stay in `gold.product_offers` but never drive verified price stats.

## Gold objects for backend handoff (Person C)
- `findora_hackathon.gold.product_offers` — offer_id, product_id, retailer, price, currency, product_url, observed_at, match_type (exact/unverified), source_type (demo).
- `findora_hackathon.gold.price_summary` — product_id, lowest_observed_price, median_observed_price, minimum_observed_price, observation_count, last_observed_at (verified-only stats).
- `findora_hackathon.silver.canonical_products` — product_id, title, brand, category, model, image_url (NULL), attributes_json.
- Canonical product IDs: `northpeak-fp-hood-100`, `trailcraft-tc-rs-200`, `basicsco-bc-tee-300`, `denimworks-dw-jn-400`, `northpeak-np-bn-500`.
- Buy/wait advice inputs: median vs current lowest; return INSUFFICIENT_DATA when observation_count < 3 (all seed products have >= 5).

## In progress
- None at commit time.

## Next steps
- Backend (Person C): Databricks adapter for `/products/search`, `/products/{id}/offers`, `/history`, `/advice` reading the Gold objects above; switch `data_mode` from demo to observed once verified.
- Replace/augment seed data with documented real data sources (provenance + original URLs + collection method) when chosen.
- Databricks App (small product lookup on Gold data) — NOT deployed yet, deliberately deferred per team decision 2026-11-14; remember Free Edition apps stop after 24h — redeploy/check Sunday morning before 2 PM judging.

## Blockers / dependencies
- Awaiting decision on real product/price source and historical dataset (docs/design.md open decision).
- All current data is labeled seed-demo — must not be presented as observed retailer data.

## Changed files / tests and outcomes
- 2026-11-14: added `databricks/sql/01_bronze.sql`, `02_silver.sql`, `03_gold.sql`; executed on serverless SQL; validation queries above all passed (counts, ID consistency, labeling, layer trace, validation.sql). `bronze_template.sql` kept as reference template. No shared contract files modified.

## Handoff notes
- Update after each meaningful commit.
