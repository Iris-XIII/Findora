-- Optional manual setup. The notebook creates this automatically.
-- Replace workspace with an existing writable catalog.
USE CATALOG workspace;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE VOLUME IF NOT EXISTS bronze.serpapi_raw;
CREATE TABLE IF NOT EXISTS bronze.raw_offers (
 source STRING, source_product_id STRING, raw_title STRING,
 brand STRING, model STRING, variant STRING, price DOUBLE,
 currency STRING, product_url STRING, observed_at TIMESTAMP,
 ingestion_batch STRING, provenance STRING
) USING DELTA;
