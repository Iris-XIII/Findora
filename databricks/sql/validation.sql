-- Replace names with actual Unity Catalog paths before running.
-- Verify real pipeline: raw -> cleaned -> served.
SELECT COUNT(*) AS raw_rows FROM findora_hackathon.bronze.raw_offers;
SELECT COUNT(*) AS canonical_products FROM findora_hackathon.silver.canonical_products;
SELECT COUNT(*) AS normalized_offers FROM findora_hackathon.silver.normalized_offers;
SELECT COUNT(*) AS served_offers FROM findora_hackathon.gold.product_offers;
SELECT product_id, MIN(price) AS lowest_price, COUNT(*) AS offer_count
FROM findora_hackathon.gold.product_offers
GROUP BY product_id
ORDER BY offer_count DESC
LIMIT 10;
