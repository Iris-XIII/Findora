-- B -> C handoff examples for the unified contract (2026-11-15).
-- :product_id and :query are bound parameters, not string substitutions.
-- Catalog: findora_hackathon (proposed shared catalog; confirm with C).
USE CATALOG findora_hackathon;
SET TIME ZONE 'UTC';

-- GET /products/search?q=...
SELECT product_id, title, brand, category, image_url,
       CAST(NULL AS STRING) AS description, data_status
FROM gold.product_catalog
WHERE contains(lower(title), lower(:query))
ORDER BY title LIMIT 50;

-- GET /products/{id}
SELECT product_id, title, brand, category, image_url,
       CAST(NULL AS STRING) AS description, data_status
FROM gold.product_catalog WHERE product_id = :product_id;

-- GET /products/{id}/offers
SELECT offer_id, retailer, price, currency, product_url AS url,
       observed_at, match_type, source_type
FROM gold.current_offers WHERE product_id = :product_id
ORDER BY price, retailer;

-- GET /products/{id}/history
SELECT observed_at, price, currency, retailer, source_type
FROM gold.product_offers WHERE product_id = :product_id ORDER BY observed_at;

-- ADVICE ELIGIBILITY (unified contract): a fresh verified current price plus
-- sufficient REAL history. HARD RULE: demo data is never advice-eligible,
-- even when it satisfies the >=3 distinct UTC dates / >=48h span thresholds.
SELECT pc.product_id, pc.data_status, cov.history_status,
       cov.distinct_observation_dates, cov.span_hours,
       cps.current_lowest_price, cps.current_last_observed_at,
       s.median_observed_price, s.minimum_observed_price,
       CASE WHEN pc.data_status <> 'demo'
             AND cov.history_status = 'sufficient'
             AND cps.current_lowest_price IS NOT NULL
            THEN 'eligible' ELSE 'not_eligible' END AS advice_eligibility
FROM gold.product_catalog pc
LEFT JOIN gold.price_coverage cov USING (product_id)
LEFT JOIN gold.current_price_summary cps USING (product_id)
LEFT JOIN gold.price_summary s USING (product_id)
WHERE pc.product_id = :product_id;
-- BUY/WAIT logic (C): only when advice_eligibility = 'eligible'; compare
-- cps.current_lowest_price against s.median_observed_price (e.g. BUY when
-- current lowest >= 10% below median); otherwise return INSUFFICIENT_DATA.

-- Inputs to C's alternatives ranking: exclude exact product, return real price or null.
-- C chooses the compatible categories/features and supplies the similarity rationale.
SELECT p.product_id, p.title, p.brand, p.category, p.attributes_json,
       s.lowest_observed_price AS price
FROM gold.product_catalog p LEFT JOIN gold.price_summary s USING (product_id)
WHERE p.product_id <> :product_id;
