-- B -> C handoff examples. Set catalog in connection or USE CATALOG first.
-- :product_id and :query are bound parameters, not string substitutions.
-- Confirm the proposed Gold semantics in README.md with C before integration.
USE CATALOG workspace;
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

-- Inputs to C's advice rule: do not interpret row count as temporal coverage.
SELECT s.*, c.distinct_observation_dates, c.first_observed_at
FROM gold.price_summary s JOIN gold.price_coverage c USING (product_id)
WHERE s.product_id = :product_id;

-- Inputs to C's alternatives ranking: exclude exact product, return real price or null.
-- C chooses the compatible categories/features and supplies the similarity rationale.
SELECT p.product_id, p.title, p.brand, p.category, p.attributes_json,
       s.lowest_observed_price AS price
FROM gold.product_catalog p LEFT JOIN gold.price_summary s USING (product_id)
WHERE p.product_id <> :product_id;
