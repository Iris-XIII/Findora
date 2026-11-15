-- Findora validation for the UNIFIED contract (2026-11-15).
-- Run after sql/01-03 (seed path) and/or notebooks/01_ingest (real path).
-- Catalog: findora_hackathon (the proposed shared catalog).
-- Record ACTUAL counts and results in docs/progress/databricks.md; never
-- assume counts. Seed demo expectations (26/5/26 rows) apply only when the
-- seed pipeline has been run and no real data has been ingested yet.

USE CATALOG findora_hackathon;
SET TIME ZONE 'UTC';

-- Layer counts (both ingestion paths share these tables).
SELECT 'bronze.raw_offers' AS object_name, COUNT(*) AS rows FROM bronze.raw_offers
UNION ALL SELECT 'silver.canonical_products', COUNT(*) FROM silver.canonical_products
UNION ALL SELECT 'silver.normalized_offers', COUNT(*) FROM silver.normalized_offers
UNION ALL SELECT 'gold.product_offers', COUNT(*) FROM gold.product_offers
UNION ALL SELECT 'gold.price_summary', COUNT(*) FROM gold.price_summary
UNION ALL SELECT 'gold.current_offers', COUNT(*) FROM gold.current_offers;

-- Integrity checks: each result must be 0.
SELECT COUNT(*) AS invalid_offers FROM gold.product_offers
WHERE price <= 0 OR isnan(price) OR price IS NULL OR currency <> 'USD'
   OR product_url IS NULL OR observed_at IS NULL;
SELECT COUNT(*) AS unlabeled_source_type FROM gold.product_offers
WHERE source_type NOT IN ('demo', 'snapshot');
SELECT COUNT(*) AS missing_provenance FROM gold.product_offers
WHERE provenance IS NULL OR provenance = '';
SELECT COUNT(*) AS orphan_offers FROM gold.product_offers o
LEFT ANTI JOIN silver.canonical_products p ON o.product_id = p.product_id;
SELECT COUNT(*) AS duplicate_offer_ids FROM (
  SELECT offer_id FROM silver.normalized_offers GROUP BY offer_id HAVING COUNT(*) > 1
);
SELECT COUNT(*) AS duplicate_bronze_candidates FROM (
  SELECT get_json_object(provenance, '$.candidate_id') FROM bronze.raw_offers
  WHERE get_json_object(provenance, '$.candidate_id') IS NOT NULL
  GROUP BY get_json_object(provenance, '$.candidate_id') HAVING COUNT(*) > 1
);
SELECT COUNT(*) AS stale_current_offers FROM gold.current_offers
WHERE observed_at < current_timestamp() - INTERVAL 24 HOURS;

-- Verified-only summary check: observation_count must equal exact offers.
-- Expected: 0 rows (unverified offers never drive price_summary).
SELECT s.product_id, s.observation_count,
       COUNT(CASE WHEN o.match_type = 'exact' THEN 1 END) AS exact_offers
FROM gold.price_summary s LEFT JOIN gold.product_offers o USING (product_id)
GROUP BY s.product_id, s.observation_count
HAVING s.observation_count <> COUNT(CASE WHEN o.match_type = 'exact' THEN 1 END);

-- Provenance separation: seed rows are plain 'seed-demo:' strings; real rows
-- are JSON with candidate_id and (for offers) verification evidence.
SELECT source_type, COUNT(*) AS offers, COUNT(DISTINCT product_id) AS products
FROM gold.product_offers GROUP BY source_type;
SELECT source, COUNT(*) AS raw_rows,
       COUNT(get_json_object(provenance, '$.candidate_id')) AS with_candidate_id
FROM bronze.raw_offers GROUP BY source ORDER BY raw_rows DESC;

-- REVOCATION AUDIT: revoked/disputed approvals keep their rows for history
-- (bronze + silver + gold) but carry match_type='revoked' and never appear
-- in any exact-only object that drives current prices or advice.
SELECT match_type, COUNT(*) AS offers FROM gold.product_offers GROUP BY match_type;
SELECT COUNT(*) AS non_exact_in_current_offers FROM gold.current_offers
WHERE match_type <> 'exact'; -- must be 0

-- DEMO/REAL SEPARATION (HARD RULE): demo observations never qualify for real
-- BUY/WAIT advice, even with >=3 distinct UTC dates spanning >=48h.
SELECT pc.product_id, pc.data_status, cov.history_status,
       cps.current_lowest_price,
       CASE WHEN pc.data_status <> 'demo' AND cov.history_status = 'sufficient'
                 AND cps.current_lowest_price IS NOT NULL
            THEN 'eligible' ELSE 'not_eligible' END AS advice_eligibility
FROM gold.product_catalog pc
LEFT JOIN gold.price_coverage cov USING (product_id)
LEFT JOIN gold.current_price_summary cps USING (product_id)
ORDER BY pc.product_id;
-- Expected: every data_status='demo' row shows history_status='demo' and
-- advice_eligibility='not_eligible', regardless of dates/span.

-- Coverage: aim for >= 2 current retailers for at least one exact product.
SELECT product_id, MIN(price) AS lowest_listed_price,
       COUNT(DISTINCT lower(trim(retailer))) AS retailer_count
FROM gold.current_offers GROUP BY product_id ORDER BY retailer_count DESC;
SELECT * FROM gold.price_summary ORDER BY product_id;
SELECT * FROM gold.current_price_summary ORDER BY product_id;
SELECT * FROM gold.price_coverage ORDER BY product_id;

-- Trace a real served value to its raw record and approval evidence.
SELECT g.product_id, g.retailer, g.price, g.observed_at, b.ingestion_batch,
       get_json_object(g.provenance, '$.search_id') AS search_id,
       get_json_object(g.provenance, '$.verification.evidence_url') AS verification_url,
       b.raw_title, b.product_url
FROM gold.product_offers g JOIN bronze.raw_offers b
  ON get_json_object(g.provenance, '$.candidate_id') = get_json_object(b.provenance, '$.candidate_id')
WHERE g.source_type = 'snapshot'
LIMIT 10;

-- Trace the seed path (bronze -> silver -> gold, demo-labeled).
SELECT offer_id, product_id, retailer, price, observed_at, match_type, source_type
FROM gold.product_offers WHERE source_type = 'demo'
ORDER BY product_id, observed_at LIMIT 30;

-- Idempotency: re-run sql/01-03 and/or the notebook on identical inputs, then
-- compare every count above with the first run. Counts must NOT grow.
