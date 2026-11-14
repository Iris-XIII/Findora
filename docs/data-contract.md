# Databricks data contract v0.1

## Proposed Unity Catalog namespace
`findora_hackathon` catalog, schemas `bronze`, `silver`, `gold` (subject to actual workspace privileges). If custom catalog creation unavailable, use the accessible catalog and record exact names in `docs/progress/databricks.md`.

## Bronze: `bronze.raw_offers`
`source STRING, source_product_id STRING, raw_title STRING, brand STRING, model STRING, variant STRING, price DOUBLE, currency STRING, product_url STRING, observed_at TIMESTAMP, ingestion_batch STRING, provenance STRING`

## Silver: `silver.canonical_products`
`product_id STRING, title STRING, brand STRING, category STRING, model STRING, image_url STRING, attributes_json STRING`

## Silver: `silver.normalized_offers`
`offer_id STRING, product_id STRING, retailer STRING, price DOUBLE, currency STRING, product_url STRING, observed_at TIMESTAMP, match_type STRING, provenance STRING`

## Gold: `gold.product_offers`
Same fields as normalized offers plus `source_type STRING`. Filter invalid prices, deduplicate by retailer/product/variant/timestamp as appropriate.

## Gold: `gold.price_summary`
`product_id STRING, lowest_observed_price DOUBLE, median_observed_price DOUBLE, minimum_observed_price DOUBLE, observation_count BIGINT, last_observed_at TIMESTAMP`

## Contract rules
- Only mark `match_type=exact` after SKU/model/variant confirmation.
- `product_id` is canonical and must match API IDs.
- Do not mix currencies without explicit conversion and rate provenance.
- Preserve observed timestamp and original source.
- One observation per documented source/time; don't generate synthetic time-series and present it as observed.
- Person B provides SQL query names/permissions; Person C adapts results to the HTTP API.
