-- Replace workspace with the catalog used by the notebook.
USE CATALOG workspace;
SET TIME ZONE 'UTC';

SELECT 'bronze.raw_offers' AS object_name, COUNT(*) AS rows FROM bronze.raw_offers
UNION ALL SELECT 'silver.canonical_products', COUNT(*) FROM silver.canonical_products
UNION ALL SELECT 'silver.normalized_offers', COUNT(*) FROM silver.normalized_offers
UNION ALL SELECT 'gold.product_offers', COUNT(*) FROM gold.product_offers
UNION ALL SELECT 'gold.current_offers', COUNT(*) FROM gold.current_offers;

-- Integrity checks: each result must be 0.
SELECT COUNT(*) AS invalid_offers FROM gold.product_offers
WHERE price <= 0 OR isnan(price) OR price IS NULL OR currency <> 'USD'
   OR product_url IS NULL OR observed_at IS NULL OR match_type <> 'exact';
SELECT COUNT(*) AS orphan_offers FROM gold.product_offers o
LEFT ANTI JOIN silver.canonical_products p ON o.product_id = p.product_id;
SELECT COUNT(*) AS duplicate_ids FROM (
  SELECT offer_id FROM silver.normalized_offers GROUP BY offer_id HAVING COUNT(*) > 1
);
SELECT COUNT(*) AS duplicate_bronze_candidates FROM (
  SELECT get_json_object(provenance, '$.candidate_id') FROM bronze.raw_offers
  GROUP BY get_json_object(provenance, '$.candidate_id') HAVING COUNT(*) > 1
);
SELECT COUNT(*) AS stale_current_offers FROM gold.current_offers
WHERE observed_at < current_timestamp() - INTERVAL 24 HOURS;

-- Coverage: aim for >= 2 current retailers for at least one exact product.
SELECT product_id, MIN(price) AS lowest_listed_price,
       COUNT(DISTINCT lower(trim(retailer))) AS retailer_count
FROM gold.current_offers GROUP BY product_id ORDER BY retailer_count DESC;
SELECT * FROM gold.price_summary;
SELECT * FROM gold.price_coverage;

-- Trace an actual served value to its raw record and approval evidence.
SELECT g.product_id, g.retailer, g.price, g.observed_at, b.ingestion_batch,
       get_json_object(g.provenance, '$.search_id') AS search_id,
       get_json_object(g.provenance, '$.verification.evidence_url') AS verification_url,
       b.raw_title, b.product_url
FROM gold.current_offers g JOIN bronze.raw_offers b
  ON get_json_object(g.provenance, '$.candidate_id') = get_json_object(b.provenance, '$.candidate_id')
LIMIT 10;

-- Re-run the notebook on identical inputs, then compare counts and IDs with the first run.
