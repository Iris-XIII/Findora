-- Findora Silver layer: canonical products + normalized offers.
-- Run after 01_bronze.sql. Fully recomputed from Bronze (idempotent).
--
-- product_id convention (stable across layers, matches API IDs):
--   lower(brand) || '-' || lower(model with non-alphanumerics as '-')
--   e.g. NorthPeak / FP-HOOD-100 -> 'northpeak-fp-hood-100'
-- match_type rule (docs/data-contract.md):
--   'exact' only when the raw variant equals the canonical variant for the
--   product (variant confirmed); otherwise 'unverified'.

SET TIME ZONE 'UTC';

CREATE SCHEMA IF NOT EXISTS findora_hackathon.silver;

-- Canonical variant per product = most frequent raw variant (ties -> alphabetical).
CREATE OR REPLACE TABLE findora_hackathon.silver.canonical_products AS
WITH variant_counts AS (
  SELECT brand, model, variant, COUNT(*) AS cnt
  FROM findora_hackathon.bronze.raw_offers
  GROUP BY brand, model, variant
),
canonical_variant AS (
  SELECT brand, model, variant
  FROM (
    SELECT brand, model, variant,
           ROW_NUMBER() OVER (PARTITION BY brand, model ORDER BY cnt DESC, variant) AS rn
    FROM variant_counts
  )
  WHERE rn = 1
)
SELECT
  CONCAT(LOWER(b.brand), '-', LOWER(REGEXP_REPLACE(b.model, '[^A-Za-z0-9]+', '-'))) AS product_id,
  MIN(b.raw_title) AS title,
  b.brand AS brand,
  CASE
    WHEN b.model LIKE 'FP-HOOD%' THEN 'Hoodies'
    WHEN b.model LIKE 'TC-RS%'   THEN 'Jackets'
    WHEN b.model LIKE 'BC-TEE%'  THEN 'T-Shirts'
    WHEN b.model LIKE 'DW-JN%'   THEN 'Jeans'
    WHEN b.model LIKE 'NP-BN%'   THEN 'Accessories'
    ELSE 'Other'
  END AS category,
  b.model AS model,
  CAST(NULL AS STRING) AS image_url,
  TO_JSON(NAMED_STRUCT('variant', cv.variant, 'brand', b.brand, 'model', b.model)) AS attributes_json
FROM findora_hackathon.bronze.raw_offers b
JOIN canonical_variant cv ON b.brand = cv.brand AND b.model = cv.model
GROUP BY b.brand, b.model, cv.variant;

COMMENT ON TABLE findora_hackathon.silver.canonical_products IS
  'Canonical products derived from bronze.raw_offers. Current contents are seed-demo data for MadHack 2026.';

-- Normalized offers: retailer comes from bronze `source`; deduplicate by
-- product/retailer/variant/timestamp keeping the newest ingestion batch.
CREATE OR REPLACE TABLE findora_hackathon.silver.normalized_offers AS
WITH canonical_variant AS (
  SELECT brand, model, variant
  FROM (
    SELECT brand, model, variant,
           ROW_NUMBER() OVER (PARTITION BY brand, model ORDER BY cnt DESC, variant) AS rn
    FROM (SELECT brand, model, variant, COUNT(*) AS cnt
          FROM findora_hackathon.bronze.raw_offers
          GROUP BY brand, model, variant)
  )
  WHERE rn = 1
),
joined AS (
  SELECT
    CONCAT(LOWER(b.brand), '-', LOWER(REGEXP_REPLACE(b.model, '[^A-Za-z0-9]+', '-'))) AS product_id,
    b.source AS retailer,
    b.price,
    b.currency,
    b.product_url,
    b.observed_at,
    b.variant,
    b.ingestion_batch,
    b.provenance,
    CASE WHEN b.variant = cv.variant THEN 'exact' ELSE 'unverified' END AS match_type
  FROM findora_hackathon.bronze.raw_offers b
  JOIN canonical_variant cv ON b.brand = cv.brand AND b.model = cv.model
),
deduped AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY product_id, retailer, variant, observed_at
           ORDER BY ingestion_batch DESC, provenance
         ) AS rn
  FROM joined
)
SELECT
  CONCAT(product_id, '-', LOWER(REGEXP_REPLACE(retailer, '[^A-Za-z0-9]+', '-')),
         '-', DATE_FORMAT(observed_at, 'yyyyMMdd-HHmmss')) AS offer_id,
  product_id,
  retailer,
  price,
  currency,
  product_url,
  observed_at,
  match_type,
  provenance
FROM deduped
WHERE rn = 1;

COMMENT ON TABLE findora_hackathon.silver.normalized_offers IS
  'Normalized offers derived from bronze.raw_offers. Current contents are seed-demo data for MadHack 2026.';
