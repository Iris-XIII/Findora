-- ONE-TIME MIGRATION (2026-11-15): add `provenance STRING` to an EXISTING
-- findora_hackathon.gold.product_offers table created before the unified
-- contract. Run ONCE, immediately before rerunning sql/03_gold.sql.
--
-- Why a separate file: Databricks does not support
-- ALTER TABLE ... ADD COLUMN IF NOT EXISTS (PARSE_SYNTAX_ERROR, verified live
-- on serverless 2026-11-15), so the idempotence guard cannot live in the SQL
-- itself. Fresh installs never need this migration: sql/03_gold.sql's
-- CREATE TABLE IF NOT EXISTS already defines the complete schema. The
-- real-data path (findora_data/pipeline.py::create_gold) adds any missing
-- columns guarded by an information_schema check.
--
-- SCOPE: adds provenance ONLY. source_type already exists in the current
-- deployment and is intentionally NOT touched.
--
-- AFTER this migration, rerunning sql/03_gold.sql backfills provenance for
-- all existing rows via its MERGE (UPDATE SET * matches by offer_id); no
-- rows are rewritten, deleted, or lost.

ALTER TABLE findora_hackathon.gold.product_offers
  ADD COLUMN provenance STRING;