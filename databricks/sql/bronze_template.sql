-- Template only. Run in a catalog/schema where you have permission.
CREATE TABLE IF NOT EXISTS findora_hackathon.bronze.raw_offers (
 source STRING, source_product_id STRING, raw_title STRING,
 brand STRING, model STRING, variant STRING, price DOUBLE,
 currency STRING, product_url STRING, observed_at TIMESTAMP,
 ingestion_batch STRING, provenance STRING
) USING DELTA;
