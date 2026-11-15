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

    # Full archive is required so removing an approval can safely retract an offer.
    missing = spark.sql(f"""
        SELECT 1 FROM {cat}.bronze.raw_offers old
        LEFT ANTI JOIN _findora_raw incoming
        ON get_json_object(old.provenance, '$.candidate_id') = get_json_object(incoming.provenance, '$.candidate_id')
        LIMIT 1
    """).count()
    if missing:
        raise ValueError("Raw input is incomplete. Restore the full archive before rebuilding Silver.")
    changed_identity = spark.sql(f"""
        SELECT 1 FROM {cat}.silver.canonical_products old
        LEFT JOIN _findora_products incoming ON old.product_id = incoming.product_id
        WHERE incoming.product_id IS NULL OR NOT (old.model <=> incoming.model)
           OR NOT (old.brand <=> incoming.brand) OR NOT (old.attributes_json <=> incoming.attributes_json)
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
    spark.sql(f"""
        MERGE INTO {cat}.silver.normalized_offers t USING _findora_offers s
        ON t.offer_id = s.offer_id
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
        WHEN NOT MATCHED BY SOURCE THEN DELETE
    """)
    create_gold(spark, cat)
    return {name: spark.table(f"{cat}.{name}").count() for name in (
        *SCHEMAS, "gold.product_offers", "gold.current_offers", "gold.price_summary")}


def create_gold(spark, cat):
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.product_offers AS
        SELECT *, 'snapshot' AS source_type
        FROM {cat}.silver.normalized_offers
        WHERE price > 0 AND NOT isnan(price) AND currency = 'USD'
          AND observed_at <= current_timestamp() AND match_type = 'exact'
    """)
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
        ) WHERE rn = 1 AND observed_at >= current_timestamp() - INTERVAL 24 HOURS
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.price_summary AS
        SELECT h.product_id, c.lowest_observed_price,
               h.median_observed_price, h.minimum_observed_price,
               h.observation_count, h.last_observed_at
        FROM (
            SELECT product_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_observed_price,
                   MIN(price) AS minimum_observed_price, COUNT(*) AS observation_count,
                   MAX(observed_at) AS last_observed_at
            FROM {cat}.gold.product_offers GROUP BY product_id
        ) h LEFT JOIN (
            SELECT product_id, MIN(price) AS lowest_observed_price
            FROM {cat}.gold.current_offers GROUP BY product_id
        ) c ON h.product_id = c.product_id
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.price_coverage AS
        SELECT product_id, COUNT(DISTINCT CAST(observed_at AS DATE)) AS distinct_observation_dates,
               MIN(observed_at) AS first_observed_at, MAX(observed_at) AS last_observed_at
        FROM {cat}.gold.product_offers GROUP BY product_id
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {cat}.gold.product_catalog AS
        SELECT p.*, CASE WHEN s.product_id IS NULL THEN 'insufficient' ELSE 'observed' END AS data_status
        FROM {cat}.silver.canonical_products p
        LEFT JOIN {cat}.gold.price_summary s ON p.product_id = s.product_id
    """)
