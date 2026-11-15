"""Unified-contract structural tests (2026-11-15).

These cover both ingestion paths (seed SQL scripts + findora_data pipeline),
provenance separation, insert/update-only safety, the unified Gold contract,
the shared catalog, and the demo hard rule. They read repository files only;
no cloud resources are touched.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the databricks/ folder


def read(*parts):
    return Path(ROOT, *parts).read_text()


class SharedCatalogTests(unittest.TestCase):
    def test_all_artifacts_reference_findora_hackathon(self):
        self.assertIn("findora_hackathon", read("sql", "validation.sql"))
        self.assertIn("findora_hackathon", read("sql", "backend_queries.sql"))
        self.assertIn("findora_hackathon", read("app", "app.yaml"))
        self.assertIn("findora_hackathon", read("app", "app.py"))

    def test_notebook_defaults_to_shared_catalog(self):
        notebook = read("notebooks", "01_ingest.py")
        self.assertIn('dbutils.widgets.text("catalog", "findora_hackathon"', notebook)
        self.assertNotIn('"catalog", "workspace"', notebook)
        self.assertNotIn("codex/databricks-serpapi", notebook)


class InsertOnlySafetyTests(unittest.TestCase):
    def test_seed_sql_has_no_destructive_operations(self):
        for name in ("01_bronze.sql", "02_silver.sql", "03_gold.sql"):
            sql = read("sql", name)
            # Statement patterns, not bare words: comments may legitimately say
            # "this script never truncates".
            self.assertNotRegex(sql, r"(?i)\bTRUNCATE\s+TABLE\b", name)
            self.assertNotRegex(sql, r"(?i)\bDELETE\s+FROM\b", name)
            self.assertNotRegex(sql, r"(?i)CREATE\s+OR\s+REPLACE\s+TABLE", name)
            self.assertNotRegex(sql, r"(?i)WHEN\s+NOT\s+MATCHED\s+BY\s+SOURCE\s+THEN\s+DELETE", name)

    def test_pipeline_merges_have_no_delete_clause(self):
        pipeline = read("findora_data", "pipeline.py")
        self.assertNotRegex(pipeline, r"(?i)WHEN\s+NOT\s+MATCHED\s+BY\s+SOURCE\s+THEN\s+DELETE")
        self.assertNotRegex(pipeline, r"(?i)\bTRUNCATE\s+TABLE\b")
        self.assertNotRegex(pipeline, r"(?i)\bDELETE\s+FROM\b")

    def test_gold_or_replace_is_views_only(self):
        gold = read("sql", "03_gold.sql").upper()
        self.assertNotRegex(gold, r"CREATE\s+OR\s+REPLACE\s+TABLE")
        self.assertRegex(gold, r"CREATE\s+OR\s+REPLACE\s+VIEW")

    def test_seed_derivation_scoped_to_seed_provenance(self):
        silver = read("sql", "02_silver.sql")
        # Every read of bronze.raw_offers in the seed path must filter to seed rows.
        self.assertGreaterEqual(silver.count("provenance LIKE 'seed-demo%'"), 4)

    def test_seed_rows_still_labeled(self):
        self.assertIn("seed-demo:", read("sql", "01_bronze.sql"))

    def test_pipeline_archive_and_identity_checks_scoped_to_real_provenance(self):
        pipeline = read("findora_data", "pipeline.py")
        self.assertIn("$.source') IN ('serpapi', 'manual_snapshot')", pipeline)
        self.assertEqual(pipeline.count("$.source') IN ('serpapi', 'manual_snapshot')"), 2)


class UnifiedGoldContractTests(unittest.TestCase):
    def test_gold_objects_defined_in_both_paths(self):
        for text, name in ((read("sql", "03_gold.sql"), "03_gold.sql"),
                           (read("findora_data", "pipeline.py"), "pipeline.py")):
            for obj in ("gold.product_offers", "gold.price_summary", "gold.current_offers",
                        "gold.current_price_summary", "gold.price_coverage", "gold.product_catalog"):
                self.assertIn(obj, text, name)

    def test_product_offers_preserves_provenance(self):
        for text in (read("sql", "03_gold.sql"), read("findora_data", "pipeline.py")):
            self.assertIn("provenance STRING", text)

    def test_price_summary_keeps_lowest_observed_price(self):
        self.assertIn("lowest_observed_price", read("sql", "03_gold.sql"))
        self.assertIn("lowest_observed_price", read("sql", "backend_queries.sql"))

    def test_demo_hard_rule_gates_advice(self):
        for text in (read("sql", "03_gold.sql"), read("findora_data", "pipeline.py")):
            # price_coverage must mark demo products 'demo', never 'sufficient'
            self.assertIn("WHEN MAX(CASE WHEN source_type = 'demo' THEN 1 ELSE 0 END) = 1 THEN 'demo'", text)
        backend = read("sql", "backend_queries.sql")
        self.assertIn("data_status <> 'demo'", backend)
        validation = read("sql", "validation.sql")
        self.assertIn("advice_eligibility", validation)
        app = read("app", "app.py")
        self.assertIn("DEMO dataset", app)


class ProductConfigTests(unittest.TestCase):
    def test_four_targets_including_gildan(self):
        products = json.loads(read("config", "products.json"))
        self.assertEqual(len(products), 4)
        gildan = [p for p in products if p["product_id"] == "gildan-18000-unisex-black-m-single"]
        self.assertEqual(len(gildan), 1)
        self.assertEqual(gildan[0]["brand"], "Gildan")
        self.assertEqual(gildan[0]["model"], "18000")
        for product in products:
            self.assertTrue(product["reference_url"].startswith("https://"), product["product_id"])

    def test_gildan_asin_discrepancy_is_documented(self):
        approvals = json.loads(read("config", "approvals.json"))
        gildan = [a for a in approvals if a["product_id"] == "gildan-18000-unisex-black-m-single"]
        self.assertEqual(len(gildan), 1)
        self.assertIn("B01M0PENYV", gildan[0]["evidence_notes"])
        self.assertIn("B0D14PTTPL", gildan[0]["evidence_notes"])
        self.assertIn("ASIN unresolved", gildan[0]["review_method"])

    def test_approvals_reference_manifest_products_only(self):
        products = {p["product_id"] for p in json.loads(read("config", "products.json"))}
        for approval in json.loads(read("config", "approvals.json")):
            self.assertIn(approval["product_id"], products)


class RevocationTests(unittest.TestCase):
    """Revoked/disputed approvals must never drive exact stats or advice."""

    def test_revoked_offers_marked_not_deleted(self):
        pipeline = read("findora_data", "pipeline.py")
        self.assertIn("SET match_type = 'revoked'", pipeline)
        self.assertIn("'$.verification.candidate_id'", pipeline)
        self.assertNotRegex(pipeline, r"(?i)\bDELETE\s+FROM\b")

    def test_revocation_scoped_to_verified_real_offers(self):
        # Only rows carrying a verification record can be revoked; seed rows
        # (plain-string provenance, no verification JSON) are never touched.
        pipeline = read("findora_data", "pipeline.py")
        self.assertIn("AND get_json_object(provenance, '$.verification.candidate_id') IS NOT NULL", pipeline)

    def test_exact_only_objects_exclude_revoked(self):
        # current_offers, price_summary, and price_coverage must all derive
        # from exact-only scans, so 'revoked' rows can never leak in.
        for text, name in ((read("sql", "03_gold.sql"), "03_gold.sql"),
                           (read("findora_data", "pipeline.py"), "pipeline.py")):
            self.assertGreaterEqual(text.count("match_type = 'exact'"), 3, name)

    def test_validation_audits_revocation(self):
        validation = read("sql", "validation.sql")
        self.assertIn("match_type='revoked'", validation)
        self.assertIn("non_exact_in_current_offers", validation)


class MergeSyntaxTests(unittest.TestCase):
    def test_no_inline_cte_in_merge_using(self):
        # Databricks does not guarantee CTEs inside MERGE USING (<subquery>);
        # all MERGE sources must be temp views or tables.
        for text, name in ((read("sql", "01_bronze.sql"), "01_bronze.sql"),
                           (read("sql", "02_silver.sql"), "02_silver.sql"),
                           (read("sql", "03_gold.sql"), "03_gold.sql"),
                           (read("findora_data", "pipeline.py"), "pipeline.py")):
            self.assertNotRegex(text, r"(?i)USING\s*\(\s*WITH", name)


class IdempotencyTests(unittest.TestCase):
    def test_stable_merge_keys(self):
        bronze = read("sql", "01_bronze.sql").upper()
        self.assertIn("ON T.SOURCE <=> S.SOURCE", bronze)
        self.assertIn("AND T.SOURCE_PRODUCT_ID <=> S.SOURCE_PRODUCT_ID", bronze)
        self.assertIn("AND T.OBSERVED_AT <=> S.OBSERVED_AT", bronze)
        gold = read("sql", "03_gold.sql")
        self.assertIn("ON t.offer_id = s.offer_id", gold)
        self.assertIn("ON t.product_id = s.product_id", gold)
        pipeline = read("findora_data", "pipeline.py")
        self.assertIn("ON t.offer_id = s.offer_id", pipeline)
        self.assertIn("'$.candidate_id') = get_json_object", pipeline)


if __name__ == "__main__":
    unittest.main()