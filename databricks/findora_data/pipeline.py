"""Databricks-only persistence. Pure normalization is independently testable."""
import re

SCHEMAS = {
    "bronze.raw_offers": "source STRING, source_product_id STRING, raw_title STRING, brand STRING, model STRING, variant STRING, price DOUBLE, currency STRING, product_url STRING, observed_at TIMESTAMP, ingestion_batch STRING, provenance STRING",
    "silver.canonical_products": "product_id STRING, title STRING, brand STRING, category STRING, model STRING, image_url STRING, attributes_json STRING",
    "silver.normalized_offers": "offer_id STRING, product_id STRING, retailer STRING, price DOUBLE, currency STRING, product_url STRING, observed_at TIMESTAMP, match_type STRING, provenance STRING",
}


def catalog_identifier(catalog):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", catalog):
        raise ValueError("Use a simple catalog name, without dots or SQL punctuation")
    return f"`{catalog}`"


def setup(spark, catalog):
    cat = catalog_identifier(catalog)
    # Do not require CREATE CATALOG; Free Edition can use its existing workspace catalog.
    spark.sql(f"USE CATALOG {cat}")
    spark.sql("SET TIME ZONE 'UTC'")
    for schema in ("bronze", "silver", "gold"):
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {cat}.{schema}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {cat}.bronze.serpapi_raw")
    for name, schema in SCHEMAS.items():
        spark.sql(f"CREATE TABLE IF NOT EXISTS {cat}.{name} ({schema}) USING DELTA")


def persist(spark, catalog, normalized):
    cat = catalog_identifier(catalog)
    setup(spark, catalog)
    tables = (("bronze.raw_offers", "bronze", "_findora_raw"),
              ("silver.canonical_products", "products", "_findora_products"),
              ("silver.normalized_offers", "offers", "_findora_offers"))
    for name, key, temp in tables:
        spark.createDataFrame(normalized[key], schema=SCHEMAS[name]).createOrReplaceTempView(temp)

    # Full archive is required so a rebuild is not silently partial. UNIFIED
    # CONTRACT (2026-11-15): scoped to REAL ingestion provenance only (serpapi /
    # manual_snapshot). Seed-demo rows written by sql/01_bronze.sql carry
    # plain-string provenance and are intentionally excluded.
    missing = spark.sql(f"""
        SELECT 1 FROM {cat}.bronze.raw_offers old
        LEFT ANTI JOIN _findora_raw incoming
        ON get_json_object(old.provenance, '$.candidate_id') = get_json_object(incoming.provenance, '$.candidate_id')
        WHERE get_json_object(old.provenance, '$.source') IN ('serpapi', 'manual_snapshot')
        LIMIT 1
    """).count()
    if missing:
        raise ValueError("Raw input is incomplete. Restore the full real-response archive before rebuilding Silver.")
    # UNIFIED CONTRACT (2026-11-15): identity protection applies only to REAL
    # products (those with real-provenance rows in Bronze). Seed-demo products
    # created by sql/02_silver.sql are legitimately absent from the manifest.
    changed_identity = spark.sql(f"""
        SELECT 1 FROM {cat}.silver.canonical_products old
        LEFT JOIN _findora_products incoming ON old.product_id = incoming.product_id
        WHERE (incoming.product_id IS NULL OR NOT (old.model <=> incoming.model)
           OR NOT (old.brand <=> incoming.brand) OR NOT (old.attributes_json <=> incoming.attributes_json))
           AND old.product_id IN (
             SELECT get_json_object(provenance, '$.target_product_id')
             FROM {cat}.bronze.raw_offers
             WHERE get_json_object(provenance, '$.source') IN ('serpapi', 'manual_snapshot')
           )
        LIMIT 1
    """).count()
    if changed_identity:
        raise ValueError("Keep existing products and their identities; use a new product_id for a new variant")

    spark.sql(f"""
        MERGE INTO {cat}.bronze.raw_offers t USING _findora_raw s
        ON get_json_object(t.provenance, '$.candidate_id') = get_json_object(s.provenance, '$.candidate_id')
        WHEN NOT MATCHED THEN INSERT *
    """)
    spark.sql(f"""
        MERGE INTO {cat}.silver.canonical_products t USING _findora_products s
        ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
    """)
    # UNIFIED CONTRACT (2026-11-15): insert/update-only; NO delete clause.
    # REVOCATION: removing/disputing an approval does NOT delete history. The
    # Silver row and its provenance (with the original verification record)
    # stay for audit, but match_type becomes 'revoked' so it stops being an
    # exact verified offer. Gold copies the label, and every exact-only object
    # (current_offers, price_summary, price_coverage, advice eligibility)
    # automatically excludes revoked offers from prices and advice.
    spark.sql(f"""
        MERGE INTO {cat}.silver.normalized_offers t USING _findora_offers s
        ON t.offer_id = s.offer_id
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
    """)
    spark.sql(f"""
        UPDATE {cat}.silver.normalized_offers
        SET match_type = 'revoked'
        WHERE match_type = 'exact'
          AND get_json_object(provenance, '$.verification.candidate_id') IS NOT NULL
          AND get_json_object(provenance, '$.verification.candidate_id') NOT IN (
              SELECT get_json_object(provenance, '$.verification.candidate_id')
              FROM _findora_offers
          )
    """)
    create_gold(spark, cat)
    return {name: spark.table(f"{cat}.{name}").count() for name in (
        *SCHEMAS, "gold.product_offers", "gold.current_offers", "gold.price_summary")}


def create_gold(spark, cat):
    """Unified Gold contract; keep in sync with sql/03_gold.sql (same semantics).

    gold.product_offers and gold.price_summary are TABLES written with
    insert/update-only MERGEs (no deletes, no wholesale rebuilds).
    current_offers / current_price_summary / price_coverage / product_catalog
    are views. DEMO HARD RULE: demo rows carry source_type='demo' and
    price_coverage marks such products 'demo' (never 'sufficient'), so demo
    data can never satisfy buy/wait advice eligibility.
    """
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {cat}.gold.product_offers (
          offer_id STRING, product_id STRING, retailer STRING, price DOUBLE,
          currency STRING, product_url STRING, observed_at TIMESTAMP,
          match_type STRING, provenance STRING, source_type STRING
        ) USING DELTA
    """)
    # Additive columns for deployments created before the unified contract.
    spark.sql(f"ALTER TABLE {cat}.gold.product_offers ADD COLUMN IF NOT EXISTS provenance STRING AFTER match_type")
    spark.sql(f"ALTER TABLE {cat}.gold.product_offers ADD COLUMN IF NOT EXISTS source_type STRING AFTER provenance")
    # Source staged in a temp view (not an inline WITH subquery) for maximum
    # Databricks SQL compatibility (same pattern as sql/03_gold.sql).
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _findora_gold_offers_source AS
        WITH valid AS (
          SELECT * FROM {cat}.silver.normalized_offers
          WHERE price IS NOT NULL AND price > 0 AND currency = 'USD'
        ),
        deduped AS (
          SELECT *, ROW_NUMBER() OVER (
            PARTITION BY product_id, retailer, observed_at, match_type
            ORDER BY offer_id
          ) AS rn
          FROM valid
        )
        SELECT offer_id, product_id, retailer, price, currency, product_url,
               observed_at, match_type, provenance,
               CASE
                 WHEN provenance LIKE 'seed-demo%' THEN 'demo'
                 WHEN get_json_object(provenance, '$.source_type') = 'snapshot' THEN 'snapshot'
                 ELSE 'unlabeled'
               END AS source_type
        FROM deduped WHERE rn = 1
    """)
    spark.sql(f"""
        MERGE INTO {cat}.gold.product_offers t USING _findora_gold_offers_source s
        ON t.offer_id = s.offer_id
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
    """)
    spark.sql("DROP VIEW IF EXISTS _findora_gold_offers_source")
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {cat}.gold.price_summary (
          product_id STRING, lowest_observed_price DOUBLE, median_observed_price DOUBLE,
          minimum_observed_price DOUBLE, observation_count BIGINT, last_observed_at TIMESTAMP
        ) USING DELTA
    """)
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _findora_gold_summary_source AS
        WITH verified AS (
          SELECT * FROM {cat}.gold.product_offers WHERE match_type = 'exact'
        ),
        latest AS (
          SELECT product_id, MAX(observed_at) AS last_observed_at
          FROM verified GROUP BY product_id
        )
        SELECT cp.product_id,
               MIN(CASE WHEN o.observed_at = l.last_observed_at THEN o.price END) AS lowest_observed_price,
               MEDIAN(o.price) AS median_observed_price,
               MIN(o.price) AS minimum_observed_price,
               COUNT(o.offer_id) AS observation_count,
               MAX(o.observed_at) AS last_observed_at
        FROM {cat}.silver.canonical_products cp
        LEFT JOIN verified o ON cp.product_id = o.product_id
        LEFT JOIN latest l ON cp.product_id = l.product_id
        GROUP BY cp.product_id
    """)
    spark.sql(f"""
        MERGE INTO {cat}.gold.price_summary t USING _findora_gold_summary_source s
        ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
    """)
    spark.sql("DROP VIEW IF EXISTS _findora_gold_summary_source")
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.current_offers AS
        SELECT offer_id, product_id, retailer, price, currency, product_url,
               observed_at, match_type, provenance, source_type
        FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY product_id, lower(trim(retailer)), currency
                ORDER BY observed_at DESC, offer_id DESC
            ) AS rn
            FROM {cat}.gold.product_offers
            WHERE match_type = 'exact'
              AND observed_at >= current_timestamp() - INTERVAL 24 HOURS
        ) WHERE rn = 1
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.current_price_summary AS
        SELECT cp.product_id, MIN(co.price) AS current_lowest_price,
               COUNT(DISTINCT lower(trim(co.retailer))) AS current_retailer_count,
               MAX(co.observed_at) AS current_last_observed_at,
               MAX(co.source_type) AS current_source_type
        FROM {cat}.silver.canonical_products cp
        LEFT JOIN {cat}.gold.current_offers co ON cp.product_id = co.product_id
        GROUP BY cp.product_id
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.price_coverage AS
        SELECT product_id,
               COUNT(DISTINCT CAST(observed_at AS DATE)) AS distinct_observation_dates,
               MIN(observed_at) AS first_observed_at, MAX(observed_at) AS last_observed_at,
               ROUND((unix_timestamp(MAX(observed_at)) - unix_timestamp(MIN(observed_at))) / 3600.0, 2) AS span_hours,
               CASE
                 WHEN MAX(CASE WHEN source_type = 'demo' THEN 1 ELSE 0 END) = 1 THEN 'demo'
                 WHEN COUNT(DISTINCT CAST(observed_at AS DATE)) >= 3
                      AND (unix_timestamp(MAX(observed_at)) - unix_timestamp(MIN(observed_at))) >= 48 * 3600
                      THEN 'sufficient'
                 ELSE 'insufficient'
               END AS history_status
        FROM {cat}.gold.product_offers WHERE match_type = 'exact' GROUP BY product_id
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.product_catalog AS
        SELECT p.product_id, p.title, p.brand, p.category, p.model, p.image_url,
               p.attributes_json,
               CASE
                 WHEN o.product_id IS NULL THEN 'unobserved'
                 WHEN o.demo_rows > 0 AND o.real_rows = 0 THEN 'demo'
                 ELSE 'observed'
               END AS data_status,
               cps.current_lowest_price
        FROM {cat}.silver.canonical_products p
        LEFT JOIN (
          SELECT product_id,
                 SUM(CASE WHEN source_type = 'demo' THEN 1 ELSE 0 END) AS demo_rows,
                 SUM(CASE WHEN source_type <> 'demo' THEN 1 ELSE 0 END) AS real_rows
          FROM {cat}.gold.product_offers GROUP BY product_id
        ) o ON p.product_id = o.product_id
        LEFT JOIN {cat}.gold.current_price_summary cps ON p.product_id = cps.product_id
    """)
