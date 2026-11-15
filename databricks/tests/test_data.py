"""Synthetic provider fixtures for unit tests only; never publish these as observed data."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from findora_data.collect import CollectionError, collect, fetch, redact
from findora_data.common import load_products
from findora_data.normalize import ATTRIBUTES, candidates, normalize
from findora_data.pipeline import catalog_identifier


def product(pid="test-jacket"):
    return {"product_id": pid, "title": "Synthetic test jacket", "query": "synthetic jacket",
            "brand": "Test Brand", "model": "TEST-1", "category": "jacket", "color": "Black",
            "size": "M Regular", "condition": "new", "currency": "USD"}


def envelope():
    return {"format_version": 1, "source_type": "snapshot", "batch_id": "synthetic-test-batch",
            "market": "us", "target_product_id": "test-jacket", "fetched_at": "2026-11-14T12:30:00Z",
            "request": {"engine": "google_immersive_product"},
            "response": {"search_metadata": {"id": "synthetic-search", "status": "Success", "created_at": "2026-11-14 12:00:00 UTC"},
                         "product_results": {"title": "Synthetic test jacket", "stores": [
                             {"name": "Test Store", "link": "https://store.example/test-jacket",
                              "price": "$50.00", "extracted_price": 50.0}]}}}


def approve(raw):
    return {"candidate_id": candidates(raw)[0]["candidate_id"], "product_id": "test-jacket",
            "confirmed": True, "price_verified": True, "available": True,
            "confirmed_attributes": {k: product()[k] for k in ATTRIBUTES},
            "evidence_url": "https://store.example/test-jacket",
            "evidence_notes": "Synthetic unit test evidence, not a real observation",
            "reviewed_at": "2026-11-14T12:30:00Z"}


class NormalizationTests(unittest.TestCase):
    def test_unreviewed_results_do_not_become_exact_offers(self):
        result = normalize([envelope()], [product()], [])
        self.assertEqual(len(result["bronze"]), 1)
        self.assertEqual(result["offers"], [])
        self.assertFalse(result["review"][0]["confirmed"])

    def test_review_preserves_identity_price_and_provenance(self):
        raw = envelope()
        row = normalize([raw], [product()], [approve(raw)])["offers"][0]
        self.assertEqual((row["product_id"], row["price"], row["currency"], row["match_type"]),
                         ("test-jacket", 50.0, "USD", "exact"))
        self.assertEqual(json.loads(row["provenance"])["source_type"], "snapshot")
        self.assertEqual(row["observed_at"].isoformat(), "2026-11-14T12:00:00+00:00")

    def test_cached_fetch_does_not_add_observation(self):
        raw = envelope()
        cached = copy.deepcopy(raw)
        cached["batch_id"] = "another-batch"
        cached["fetched_at"] = "2026-11-14T12:59:00Z"
        result = normalize([raw, cached], [product()], [approve(raw)])
        self.assertEqual(len(result["bronze"]), 1)
        self.assertEqual(len(result["offers"]), 1)

    def test_new_source_observation_needs_new_review(self):
        old = envelope()
        new = copy.deepcopy(old)
        new["response"]["search_metadata"].update(id="new-search", created_at="2026-11-14 13:00:00 UTC")
        new["fetched_at"] = "2026-11-14T13:30:00Z"
        result = normalize([old, new], [product()], [approve(old)])
        self.assertEqual(len(result["bronze"]), 2)
        self.assertEqual(len(result["offers"]), 1)

    def test_size_color_model_currency_and_condition_mismatch_fail(self):
        raw = envelope()
        for key in ATTRIBUTES:
            with self.subTest(key=key):
                approval = approve(raw)
                approval["confirmed_attributes"][key] = "WRONG"
                with self.assertRaisesRegex(ValueError, "attributes"):
                    normalize([raw], [product()], [approval])

    def test_invalid_price_and_currency_are_retained_only_in_bronze(self):
        for value in (None, "50", -1, 0, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                raw = envelope()
                raw["response"]["product_results"]["stores"][0]["extracted_price"] = value
                result = normalize([raw], [product()], [])
                self.assertIsNone(result["bronze"][0]["price"])
                with self.assertRaisesRegex(ValueError, "invalid candidate"):
                    normalize([raw], [product()], [approve(raw)])
        raw = envelope()
        raw["response"]["product_results"]["stores"][0]["currency"] = "CAD"
        with self.assertRaisesRegex(ValueError, "currency"):
            normalize([raw], [product()], [approve(raw)])

    def test_missing_source_time_is_not_replaced_with_fetch_time(self):
        raw = envelope()
        del raw["response"]["search_metadata"]["created_at"]
        with self.assertRaises(ValueError):
            normalize([raw], [product()], [])

    def test_google_link_cannot_be_served_as_merchant_link(self):
        raw = envelope()
        raw["response"]["product_results"]["stores"][0]["link"] = "https://www.google.com/shopping/product/123"
        self.assertIn("missing_direct_merchant_url", candidates(raw)[0]["problems"])

    def test_relative_google_redirect_requires_reviewed_destination(self):
        raw = envelope()
        raw["response"]["product_results"]["stores"][0]["link"] = "/goto?url=synthetic-token"
        approval = approve(raw)
        with self.assertRaisesRegex(ValueError, "redirect requires"):
            normalize([raw], [product()], [approval])
        approval["resolved_product_url"] = "https://store.example/test-jacket"
        approval["resolved_from"] = "https://www.google.com/goto?url=synthetic-token"
        result = normalize([raw], [product()], [approval])
        self.assertEqual(result["bronze"][0]["product_url"], "/goto?url=synthetic-token")
        self.assertEqual(result["offers"][0]["product_url"], "https://store.example/test-jacket")
        self.assertEqual(result["review"][0]["review_url"], approval["resolved_from"])
        self.assertIn("url_resolution", json.loads(result["offers"][0]["provenance"]))

    def test_resolved_redirect_cannot_remove_other_rejections(self):
        raw = envelope()
        raw["response"]["product_results"]["stores"][0].update(link="/goto?url=synthetic-token", currency="CAD")
        approval = approve(raw)
        approval.update(resolved_product_url="https://store.example/test-jacket",
                        resolved_from="https://www.google.com/goto?url=synthetic-token")
        with self.assertRaisesRegex(ValueError, "currency"):
            normalize([raw], [product()], [approval])

    def test_arbitrary_relative_url_is_not_a_google_redirect(self):
        raw = envelope()
        raw["response"]["product_results"]["stores"][0]["link"] = "//malicious.example/goto?url=x"
        self.assertIn("missing_direct_merchant_url", candidates(raw)[0]["problems"])

    def test_shopping_result_parser(self):
        raw = envelope()
        raw["request"]["engine"] = "google_shopping"
        raw["response"]["shopping_results"] = [{"source": "Test Store", "title": "Synthetic jacket",
            "product_id": "provider-id", "product_link": "https://www.google.com/shopping/product/123",
            "price": "$50.00", "extracted_price": 50.0}]
        row = candidates(raw)[0]
        self.assertEqual(row["source_product_id"], "provider-id")
        self.assertEqual(row["retailer"], "Test Store")
        self.assertIn("missing_direct_merchant_url", row["problems"])

    def test_missing_or_duplicate_approval_is_rejected(self):
        raw = envelope()
        approval = approve(raw)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            normalize([raw], [product()], [approval, approval])
        approval["candidate_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "missing from raw"):
            normalize([raw], [product()], [approval])

    def test_approval_requires_same_merchant_available_variant_and_price(self):
        raw = envelope()
        for key in ("price_verified", "available"):
            approval = approve(raw)
            approval[key] = False
            with self.assertRaisesRegex(ValueError, "available"):
                normalize([raw], [product()], [approval])
        approval = approve(raw)
        approval["evidence_url"] = "https://other.example/jacket"
        with self.assertRaisesRegex(ValueError, "merchant"):
            normalize([raw], [product()], [approval])

    def test_used_item_not_approved(self):
        raw = envelope()
        raw["response"]["product_results"]["stores"][0]["second_hand_condition"] = "Used"
        with self.assertRaisesRegex(ValueError, "used_or_refurbished"):
            normalize([raw], [product()], [approve(raw)])


class CollectorTests(unittest.TestCase):
    def test_budget_reserves_discovery_for_all_targets_and_strips_key(self):
        calls = []
        def fake(params, key):
            calls.append(params)
            return {"search_parameters": {"api_key": key}, "link": f"https://serpapi.com/search?api_key={key}",
                    "shopping_results": [{"immersive_product_page_token": "one"},
                                         {"immersive_product_page_token": "one"},
                                         {"immersive_product_page_token": "two"}]}
        with tempfile.TemporaryDirectory() as folder:
            count = collect([product(), product("second")], folder, "SECRET", 3, 2, fetcher=fake)
            self.assertEqual(count, 3)
            self.assertEqual([c["engine"] for c in calls], ["google_shopping", "google_immersive_product", "google_shopping"])
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 3)
            self.assertNotIn("SECRET", "".join(p.read_text() for p in Path(folder).glob("*.json")))

    def test_successful_response_survives_later_failure(self):
        def fake(params, key):
            if params["engine"] == "google_immersive_product":
                raise CollectionError("synthetic provider failure")
            return {"shopping_results": [{"immersive_product_page_token": "one"}]}
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(CollectionError):
                collect([product()], folder, "SECRET", fetcher=fake)
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 1)

    def test_network_errors_do_not_expose_credentials(self):
        error = HTTPError("https://serpapi.com/search?api_key=SECRET", 429, "SECRET", {}, None)
        with patch("findora_data.collect.urlopen", side_effect=error):
            with self.assertRaises(CollectionError) as caught:
                fetch({"engine": "google_shopping"}, "SECRET")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertIn("429", str(caught.exception))

    def test_nested_redaction(self):
        result = redact({"API_KEY": "SECRET", "nested": [{"url": "https://x?api_key=SECRET&x=1"}]}, "SECRET")
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("API_KEY", result)

    def test_manifest_and_catalog_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "products.json"
            path.write_text(json.dumps([product(), product()]))
            with self.assertRaisesRegex(ValueError, "unique"):
                load_products(path)
        self.assertEqual(catalog_identifier("workspace"), "`workspace`")
        with self.assertRaises(ValueError):
            catalog_identifier("workspace; DROP TABLE")


if __name__ == "__main__":
    unittest.main()
