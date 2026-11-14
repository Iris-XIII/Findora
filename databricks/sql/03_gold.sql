-- Findora Gold layer: served offers + price summary.
-- Run after 02_silver.sql. Fully recomputed from Silver (idempotent).
--
-- Validity filter: price IS NOT NULL AND price > 0 AND currency = 'USD'
-- (no currency mixing per docs/data-contract.md).
-- source_type derivation from provenance:
--   provenance LIKE 'seed-demo%' -> 'demo'  (all current rows)
--   future real snapshots/live feeds should set provenance accordingly
--   ('snapshot: ...' / 'live: ...') and will map to 'snapshot' / 'live'.

SET TIME ZONE 'UTC';

CREATE SCHEMA IF NOT EXISTS findora_hackathon.gold;

CREATE OR REPLACE TABLE findora_hackathon.gold.product_offers AS
WITH valid AS (
  SELECT *
  FROM findora_hackathon.silver.normalized_offers
  WHERE price IS NOT NULL AND price > 0 AND currency = 'USD'
),
deduped AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY product_id, retailer, observed_at, match_type
           ORDER BY offer_id
         ) AS rn
  FROM valid
)
SELECT
  offer_id,
  product_id,
  retailer,
  price,
  currency,
  product_url,
  observed_at,
  match_type,
  CASE
    WHEN provenance LIKE 'seed-demo%' THEN 'demo'
    WHEN provenance LIKE 'snapshot%'  THEN 'snapshot'
    ELSE 'live'
  END AS source_type
FROM deduped
WHERE rn = 1;

COMMENT ON TABLE findora_hackathon.gold.product_offers IS
  'Served offers. Current contents are seed-demo data for MadHack 2026 (source_type=demo); not observed retailer data.';

-- Price summary per product, over VERIFIED (match_type='exact') served
-- offers only -- "cheapest means lowest verified listed price" (docs/design.md).
-- Unverified near-matches stay available in gold.product_offers for the API
-- layer to show with match_type='unverified', but do not drive the summary.
--   lowest_observed_price  = lowest verified price on the most recent observation date
--                            (i.e. current cheapest verified listed price)
--   median_observed_price  = median across ALL verified observations
--   minimum_observed_price = all-time minimum across ALL verified observations
--   observation_count      = number of verified (retailer, timestamp) observations
--   last_observed_at       = most recent verified observation timestamp
-- Products with NO verified offers still appear (one row, NULL price stats,
-- observation_count = 0) so downstream code can show an explicit
-- insufficient-coverage state instead of silently missing the product.
CREATE OR REPLACE TABLE findora_hackathon.gold.price_summary AS
WITH verified AS (
  SELECT * FROM findora_hackathon.gold.product_offers
  WHERE match_type = 'exact'
),
latest AS (
  SELECT product_id, MAX(observed_at) AS last_observed_at
  FROM verified
  GROUP BY product_id
)
SELECT
  cp.product_id,
  MIN(CASE WHEN o.observed_at = l.last_observed_at THEN o.price END) AS lowest_observed_price,
  MEDIAN(o.price) AS median_observed_price,
  MIN(o.price) AS minimum_observed_price,
  COUNT(o.offer_id) AS observation_count,
  MAX(o.observed_at) AS last_observed_at
FROM findora_hackathon.silver.canonical_products cp
LEFT JOIN verified o ON cp.product_id = o.product_id
LEFT JOIN latest l ON cp.product_id = l.product_id
GROUP BY cp.product_id;

COMMENT ON TABLE findora_hackathon.gold.price_summary IS
  'Per-product price summary over verified (exact-match) served offers. Current contents are seed-demo data for MadHack 2026.';
