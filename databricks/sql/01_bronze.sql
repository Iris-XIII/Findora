-- Findora Bronze layer: raw offers.
-- Run order: 01_bronze.sql -> 02_silver.sql -> 03_gold.sql -> validation.sql
--
-- PROVENANCE: every row below is SEED-DEMO data generated for MadHack 2026
-- on 2026-11-14. It is NOT observed retailer data. Retailers are fictional
-- names; URLs are example.com placeholders per docs/api-contract.md.
-- In this seed the bronze `source` column carries the retailer identifier;
-- Silver derives `retailer` from it.

SET TIME ZONE 'UTC';

CREATE SCHEMA IF NOT EXISTS findora_hackathon.bronze;

CREATE TABLE IF NOT EXISTS findora_hackathon.bronze.raw_offers (
  source STRING,
  source_product_id STRING,
  raw_title STRING,
  brand STRING,
  model STRING,
  variant STRING,
  price DOUBLE,
  currency STRING,
  product_url STRING,
  observed_at TIMESTAMP,
  ingestion_batch STRING,
  provenance STRING
) USING DELTA;

COMMENT ON TABLE findora_hackathon.bronze.raw_offers IS
  'Raw offers. Current contents are seed-demo data for MadHack 2026 (labeled in provenance column); not observed retailer data.';

-- Idempotent rerun (unified contract, 2026-11-15): INSERT-ONLY upsert on the
-- stable seed key (source, source_product_id, observed_at). This script never
-- truncates, deletes, or rebuilds; real rows ingested via
-- findora_data.pipeline (SerpAPI / manual provenance) are never touched.
CREATE OR REPLACE TEMP VIEW _findora_seed_raw AS
-- The alias list is REQUIRED: without it Spark names the VALUES columns
-- col1..col12 and the MERGE below cannot resolve s.source etc. (fixed after
-- live DELTA_MERGE_UNRESOLVED_EXPRESSION in Phase 1, 2026-11-15).
SELECT * FROM VALUES
  -- Product 1: NorthPeak Fleece Hoodie (FP-HOOD-100), canonical variant 'Charcoal / L'
  ('Demo Outfitters','DO-FPHOOD100-CHL','NorthPeak Fleece Hoodie','NorthPeak','FP-HOOD-100','Charcoal / L',59.99,'USD','https://example.com/demo-outfitters/fleece-hoodie',CAST('2026-11-01T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Demo Outfitters','DO-FPHOOD100-CHL','NorthPeak Fleece Hoodie','NorthPeak','FP-HOOD-100','Charcoal / L',54.99,'USD','https://example.com/demo-outfitters/fleece-hoodie',CAST('2026-11-07T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Demo Outfitters','DO-FPHOOD100-CHL','NorthPeak Fleece Hoodie','NorthPeak','FP-HOOD-100','Charcoal / L',49.99,'USD','https://example.com/demo-outfitters/fleece-hoodie',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Trailhead Supply Co.','TH-FPHOOD100-CHL','NorthPeak Fleece Hoodie','NorthPeak','FP-HOOD-100','Charcoal / L',52.99,'USD','https://example.com/trailhead-supply/fleece-hoodie',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Campus Apparel','CA-FPHOOD100-CHL','NorthPeak Fleece Hoodie','NorthPeak','FP-HOOD-100','Charcoal / L',47.99,'USD','https://example.com/campus-apparel/fleece-hoodie',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  -- Deliberate near-match: model matches but variant differs (size M vs L) -> must be match_type 'unverified' in Silver
  ('MegaMart','MM-FPHOOD100-CHM','NorthPeak Fleece Hoodie (M)','NorthPeak','FP-HOOD-100','Charcoal / M',44.99,'USD','https://example.com/megamart/fleece-hoodie-m',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),

  -- Product 2: TrailCraft Rain Shell Jacket (TC-RS-200), canonical variant 'Navy / M'
  ('Trailhead Supply Co.','TH-TCRS200-NVM','TrailCraft Rain Shell Jacket','TrailCraft','TC-RS-200','Navy / M',129.00,'USD','https://example.com/trailhead-supply/rain-shell',CAST('2026-11-01T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Trailhead Supply Co.','TH-TCRS200-NVM','TrailCraft Rain Shell Jacket','TrailCraft','TC-RS-200','Navy / M',129.00,'USD','https://example.com/trailhead-supply/rain-shell',CAST('2026-11-07T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Trailhead Supply Co.','TH-TCRS200-NVM','TrailCraft Rain Shell Jacket','TrailCraft','TC-RS-200','Navy / M',119.00,'USD','https://example.com/trailhead-supply/rain-shell',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Demo Outfitters','DO-TCRS200-NVM','TrailCraft Rain Shell Jacket','TrailCraft','TC-RS-200','Navy / M',125.00,'USD','https://example.com/demo-outfitters/rain-shell',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Uptown Threads','UT-TCRS200-NVM','TrailCraft Rain Shell Jacket','TrailCraft','TC-RS-200','Navy / M',134.50,'USD','https://example.com/uptown-threads/rain-shell',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),

  -- Product 3: BasicsCo Cotton Crew Tee (BC-TEE-300), canonical variant 'White / XL'
  ('Basics Barn','BB-BCTEE300-WXL','BasicsCo Cotton Crew Tee','BasicsCo','BC-TEE-300','White / XL',19.99,'USD','https://example.com/basics-barn/cotton-tee',CAST('2026-11-01T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Basics Barn','BB-BCTEE300-WXL','BasicsCo Cotton Crew Tee','BasicsCo','BC-TEE-300','White / XL',17.99,'USD','https://example.com/basics-barn/cotton-tee',CAST('2026-11-07T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Basics Barn','BB-BCTEE300-WXL','BasicsCo Cotton Crew Tee','BasicsCo','BC-TEE-300','White / XL',15.99,'USD','https://example.com/basics-barn/cotton-tee',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Demo Outfitters','DO-BCTEE300-WXL','BasicsCo Cotton Crew Tee','BasicsCo','BC-TEE-300','White / XL',16.99,'USD','https://example.com/demo-outfitters/cotton-tee',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Campus Apparel','CA-BCTEE300-WXL','BasicsCo Cotton Crew Tee','BasicsCo','BC-TEE-300','White / XL',18.99,'USD','https://example.com/campus-apparel/cotton-tee',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),

  -- Product 4: DenimWorks Slim Stretch Jeans (DW-JN-400), canonical variant 'Indigo / 32'
  ('Uptown Threads','UT-DWJN400-IN32','DenimWorks Slim Stretch Jeans','DenimWorks','DW-JN-400','Indigo / 32',89.00,'USD','https://example.com/uptown-threads/slim-jeans',CAST('2026-11-01T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Uptown Threads','UT-DWJN400-IN32','DenimWorks Slim Stretch Jeans','DenimWorks','DW-JN-400','Indigo / 32',84.00,'USD','https://example.com/uptown-threads/slim-jeans',CAST('2026-11-07T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Uptown Threads','UT-DWJN400-IN32','DenimWorks Slim Stretch Jeans','DenimWorks','DW-JN-400','Indigo / 32',79.00,'USD','https://example.com/uptown-threads/slim-jeans',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Demo Outfitters','DO-DWJN400-IN32','DenimWorks Slim Stretch Jeans','DenimWorks','DW-JN-400','Indigo / 32',81.50,'USD','https://example.com/demo-outfitters/slim-jeans',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Trailhead Supply Co.','TH-DWJN400-IN32','DenimWorks Slim Stretch Jeans','DenimWorks','DW-JN-400','Indigo / 32',85.00,'USD','https://example.com/trailhead-supply/slim-jeans',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),

  -- Product 5: NorthPeak Merino Beanie (NP-BN-500), canonical variant 'Gray / One Size'
  ('Campus Apparel','CA-NPBN500-GR','NorthPeak Merino Beanie','NorthPeak','NP-BN-500','Gray / One Size',24.00,'USD','https://example.com/campus-apparel/merino-beanie',CAST('2026-11-01T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Campus Apparel','CA-NPBN500-GR','NorthPeak Merino Beanie','NorthPeak','NP-BN-500','Gray / One Size',24.00,'USD','https://example.com/campus-apparel/merino-beanie',CAST('2026-11-07T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Campus Apparel','CA-NPBN500-GR','NorthPeak Merino Beanie','NorthPeak','NP-BN-500','Gray / One Size',21.50,'USD','https://example.com/campus-apparel/merino-beanie',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Basics Barn','BB-NPBN500-GR','NorthPeak Merino Beanie','NorthPeak','NP-BN-500','Gray / One Size',22.75,'USD','https://example.com/basics-barn/merino-beanie',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data'),
  ('Demo Outfitters','DO-NPBN500-GR','NorthPeak Merino Beanie','NorthPeak','NP-BN-500','Gray / One Size',23.00,'USD','https://example.com/demo-outfitters/merino-beanie',CAST('2026-11-14T12:00:00Z' AS TIMESTAMP),'seed-2026-11-14-001','seed-demo: generated for MadHack 2026 on 2026-11-14; not observed retailer data')
AS seed(source, source_product_id, raw_title, brand, model, variant,
        price, currency, product_url, observed_at, ingestion_batch, provenance);

-- Insert-only MERGE on the stable seed key. Matched rows are left untouched
-- (seed observations are immutable history); only genuinely new rows insert.
MERGE INTO findora_hackathon.bronze.raw_offers t
USING _findora_seed_raw s
ON t.source <=> s.source
   AND t.source_product_id <=> s.source_product_id
   AND t.observed_at <=> s.observed_at
WHEN NOT MATCHED THEN INSERT *;

DROP VIEW IF EXISTS _findora_seed_raw;
