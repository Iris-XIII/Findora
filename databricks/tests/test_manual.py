"""Synthetic manual observations, never real retailer evidence."""
import unittest

from findora_data.manual import make_envelope
from findora_data.normalize import candidates, normalize
from test_data import product, approve


def observation():
    return {"title": "Synthetic test jacket", "retailer": "Test Store", "source_product_id": "test-sku",
            "product_url": "https://store.example/test-jacket", "price": 50.0, "currency": "USD",
            "observed_at": "2026-11-14T12:00:00Z", "evidence_ref": "synthetic-test-screenshot",
            "evidence_notes": "Synthetic fixture only", "observation_precision": "approximate minute"}


class ManualObservationTests(unittest.TestCase):
    def envelope(self, row=None, recorded="2026-11-14T12:30:00Z"):
        return make_envelope(row or observation(), "test-jacket", recorded)

    def test_manual_snapshot_is_unapproved_and_truthfully_sourced(self):
        result = normalize([self.envelope()], [product()], [])
        self.assertEqual(result["bronze"][0]["source"], "manual_snapshot")
        self.assertEqual(result["offers"], [])
        self.assertNotIn('"search_id"', result["bronze"][0]["provenance"])

    def test_approval_uses_existing_variant_checks(self):
        raw = self.envelope()
        result = normalize([raw], [product()], [approve(raw)])
        self.assertEqual(result["offers"][0]["match_type"], "exact")
        approval = approve(raw)
        approval["confirmed_attributes"]["size"] = "WRONG"
        with self.assertRaisesRegex(ValueError, "attributes"):
            normalize([raw], [product()], [approval])

    def test_reimport_preserves_observation_time_and_identity(self):
        first = self.envelope()
        second = self.envelope(recorded="2026-11-14T13:00:00Z")
        self.assertEqual(candidates(first)[0]["candidate_id"], candidates(second)[0]["candidate_id"])
        self.assertEqual(len(normalize([first, second], [product()], [])["bronze"]), 1)

    def test_missing_evidence_or_time_is_rejected(self):
        for key in ("observed_at", "evidence_ref", "evidence_notes"):
            row = observation()
            del row[key]
            with self.assertRaises(ValueError):
                self.envelope(row)

    def test_invalid_values_are_rejected(self):
        for key, value in (("price", float("nan")), ("price", True), ("currency", "CAD"),
                           ("observed_at", "2026-11-15T12:00:00Z"), ("product_url", "https://www.google.com/search?q=test")):
            row = observation()
            row[key] = value
            with self.assertRaises(ValueError):
                self.envelope(row)


if __name__ == "__main__":
    unittest.main()
