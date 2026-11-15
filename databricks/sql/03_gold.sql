-- Findora Gold layer: unified served contract (2026-11-15).
-- Run after 02_silver.sql. Seed path writes demo rows only; real rows are
-- written by findora_data.pipeline. Keep this file in sync with
-- findora_data/pipeline.py::create_gold (identical unified semantics).
--
-- Unified Gold contract (approved 2026-11-14/15):
--   gold.product_offers        TABLE (all match types, keeps provenance +
--                              source_type demo/snapshot; insert/update-only)
--   gold.price_summary         TABLE (verified-only stats; KEEPS
--                              lowest_observed_price for backward compatibility)
--   gold.current_offers        VIEW (fresh verified offers, 24h window)
--   gold.current_price_summary VIEW (fresh current lowest; NULL when stale)
--   gold.price_coverage        VIEW (distinct UTC dates + span + history_status)
--   gold.product_catalog       VIEW (data_status: unobserved/demo/observed)
--
-- DEMO HARD RULE: demo observations never qualify for real BUY/WAIT advice,
-- even when they satisfy the >=3 distinct UTC dates / >=48h span thresholds.
-- Advice eligibility = data_status <> 'demo' AND history_status = 'sufficient'
-- AND a fresh verified current price (see sql/backend_queries.sql).

SET TIME ZONE 'UTC';

CREATE SCHEMA IF NOT EXISTS findora_hackathon.gold;

-- ------------------------------------------------------------------------
-- gold.product_offers (TABLE; provenance preserved per C's requirement)
-- Validity filter: price IS NOT NULL AND price > 0 AND currency = 'USD'.
-- ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findora_hackathon.gold.product_offers (
  offer_id STRING,
  product_id STRING,
  retailer STRING,
  price DOUBLE,
  currency STRING,
  product_url STRING,
  observed_at TIMESTAMP,
  match_type STRING,
  provenance STRING,
  source_type STRING
) USING DELTA;

-- Additive columns for deployments created before the unified contract.
ALTER TABLE findora_hackathon.gold.product_offers
  ADD COLUMN IF NOT EXISTS provenance STRING AFTER match_type;
ALTER TABLE findora_hackathon.gold.product_offers
  ADD COLUMN IF NOT EXISTS source_type STRING AFTER provenance;

-- Insert/update-only MERGE from Silver. No deletes; no wholesale rebuild.
-- Source is staged in a TEMP VIEW (not an inline WITH subquery) for maximum
-- Databricks SQL compatibility: MERGE USING (<subquery-with-CTE>) is not
-- guaranteed across runtimes, USING <view> is.
CREATE OR REPLACE TEMP VIEW _findora_gold_offers_source AS
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
  offer_id, product_id, retailer, price, currency, product_url,
  observed_at, match_type, provenance,
  CASE
    WHEN provenance LIKE 'seed-demo%' THEN 'demo'
    WHEN get_json_object(provenance, '$.source_type') = 'snapshot' THEN 'snapshot'
    ELSE 'unlabeled'
  END AS source_type
FROM deduped
WHERE rn = 1;

MERGE INTO findora_hackathon.gold.product_offers t
USING _findora_gold_offers_source s
ON t.offer_id = s.offer_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

DROP VIEW IF EXISTS _findora_gold_offers_source;

COMMENT ON TABLE findora_hackathon.gold.product_offers IS
  'Served offers, all match types, provenance preserved. source_type: demo (seed) / snapshot (reviewed real) / unlabeled (flagged by validation). Seed rows are MadHack 2026 demo data.';

-- ------------------------------------------------------------------------
-- gold.price_summary (TABLE; verified-only stats, backward compatible)
--   lowest_observed_price  = lowest verified price on the most recent
--                            observation date (current cheapest verified)
--   median_observed_price  = median across ALL verified observations
--   minimum_observed_price = all-time minimum across ALL verified
--   observation_count      = verified (retailer, timestamp) observations
--   last_observed_at       = most recent verified observation
-- Products with NO verified offers still appear (NULL stats, count 0).
-- ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findora_hackathon.gold.price_summary (
  product_id STRING,
  lowest_observed_price DOUBLE,
  median_observed_price DOUBLE,
  minimum_observed_price DOUBLE,
  observation_count BIGINT,
  last_observed_at TIMESTAMP
) USING DELTA;

-- Same insert/update-only MERGE pattern with a staged temp-view source.
CREATE OR REPLACE TEMP VIEW _findora_gold_summary_source AS
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

MERGE INTO findora_hackathon.gold.price_summary t
USING _findora_gold_summary_source s
ON t.product_id = s.product_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

DROP VIEW IF EXISTS _findora_gold_summary_source;

COMMENT ON TABLE findora_hackathon.gold.price_summary IS
  'Per-product summary over verified (exact) offers; keeps lowest_observed_price for backward compatibility. Seed rows are demo data.';

-- ------------------------------------------------------------------------
-- Gold views (definitions only; CREATE OR REPLACE VIEW is not
-- data-destructive and never touches table contents).
-- ------------------------------------------------------------------------

-- Fresh verified offers: latest per product/retailer within 24 hours.
-- The 24h window is the agreed default; a configurable window can query
-- gold.product_offers directly with a different interval.
CREATE OR REPLACE VIEW findora_hackathon.gold.current_offers AS
SELECT offer_id, product_id, retailer, price, currency, product_url,
       observed_at, match_type, provenance, source_type
FROM (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY product_id, lower(trim(retailer)), currency
           ORDER BY observed_at DESC, offer_id DESC
         ) AS rn
  FROM findora_hackathon.gold.product_offers
  WHERE match_type = 'exact'
    AND observed_at >= current_timestamp() - INTERVAL 24 HOURS
) WHERE rn = 1;

-- Fresh current lowest per product (NULL when no fresh verified offer).
CREATE OR REPLACE VIEW findora_hackathon.gold.current_price_summary AS
SELECT cp.product_id,
       MIN(co.price) AS current_lowest_price,
       COUNT(DISTINCT lower(trim(co.retailer))) AS current_retailer_count,
       MAX(co.observed_at) AS current_last_observed_at,
       MAX(co.source_type) AS current_source_type
FROM findora_hackathon.silver.canonical_products cp
LEFT JOIN findora_hackathon.gold.current_offers co
  ON cp.product_id = co.product_id
GROUP BY cp.product_id;

-- History sufficiency: >=3 distinct UTC observation dates spanning >=48h,
-- REAL data only. DEMO HARD RULE: demo products are never 'sufficient'.
CREATE OR REPLACE VIEW findora_hackathon.gold.price_coverage AS
SELECT product_id,
       COUNT(DISTINCT CAST(observed_at AS DATE)) AS distinct_observation_dates,
       MIN(observed_at) AS first_observed_at,
       MAX(observed_at) AS last_observed_at,
       ROUND((unix_timestamp(MAX(observed_at)) - unix_timestamp(MIN(observed_at))) / 3600.0, 2) AS span_hours,
       CASE
         WHEN MAX(CASE WHEN source_type = 'demo' THEN 1 ELSE 0 END) = 1 THEN 'demo'
         WHEN COUNT(DISTINCT CAST(observed_at AS DATE)) >= 3
              AND (unix_timestamp(MAX(observed_at)) - unix_timestamp(MIN(observed_at))) >= 48 * 3600
              THEN 'sufficient'
         ELSE 'insufficient'
       END AS history_status
FROM findora_hackathon.gold.product_offers
WHERE match_type = 'exact'
GROUP BY product_id;

-- Product catalog with data status for the API/App:
--   'unobserved' = no offers; 'demo' = only demo offers; 'observed' = real.
CREATE OR REPLACE VIEW findora_hackathon.gold.product_catalog AS
SELECT p.product_id, p.title, p.brand, p.category, p.model, p.image_url,
       p.attributes_json,
       CASE
         WHEN o.product_id IS NULL THEN 'unobserved'
         WHEN o.demo_rows > 0 AND o.real_rows = 0 THEN 'demo'
         ELSE 'observed'
       END AS data_status,
       cps.current_lowest_price
FROM findora_hackathon.silver.canonical_products p
LEFT JOIN (
  SELECT product_id,
         SUM(CASE WHEN source_type = 'demo' THEN 1 ELSE 0 END) AS demo_rows,
         SUM(CASE WHEN source_type <> 'demo' THEN 1 ELSE 0 END) AS real_rows
  FROM findora_hackathon.gold.product_offers
  GROUP BY product_id
) o ON p.product_id = o.product_id
LEFT JOIN findora_hackathon.gold.current_price_summary cps
  ON p.product_id = cps.product_id;
