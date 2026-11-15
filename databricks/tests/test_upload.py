"""Offline tests for private key loading and the direct-upload workflow."""
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from findora_data.collect import load_api_key
from findora_data.package_upload import build_package, copy_snapshots, reject_credentials
from test_data import envelope, product


class PrivateKeyTests(unittest.TestCase):
    def test_key_file_read_without_shell_execution(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / ".env"
            path.write_text('# Private\nOTHER=ignored\nSERPAPI_API_KEY="synthetic-key"\n')
            self.assertEqual(load_api_key(path), "synthetic-key")
            path.write_text('SERPAPI_API_KEY=$(this_is_not_executed)\n')
            self.assertEqual(load_api_key(path), "$(this_is_not_executed)")

    def test_environment_takes_precedence(self):
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "environment-test-key"}):
            self.assertEqual(load_api_key("/nonexistent/.env"), "environment-test-key")

    def test_duplicate_key_rejected_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / ".env"
            path.write_text('SERPAPI_API_KEY=synthetic-one\nSERPAPI_API_KEY=synthetic-two\n')
            with self.assertRaises(ValueError) as caught:
                load_api_key(path)
            self.assertNotIn("synthetic", str(caught.exception))


class UploadTests(unittest.TestCase):
    def test_snapshot_copy_is_idempotent_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as folder:
            source, dest = Path(folder) / "source", Path(folder) / "dest"
            source.mkdir()
            (source / "one.json").write_text('{"test": 1}')
            self.assertEqual(copy_snapshots(source, dest), 1)
            self.assertEqual(copy_snapshots(source, dest), 0)
            (dest / "older.json").write_text('{"older": true}')
            self.assertEqual(copy_snapshots(source, dest), 0)
            self.assertTrue((dest / "older.json").exists())

    def test_snapshot_conflict_prevents_partial_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            source, dest = Path(folder) / "source", Path(folder) / "dest"
            source.mkdir()
            dest.mkdir()
            (source / "a.json").write_text('{}')
            (source / "z.json").write_text('{"test": 1}')
            (dest / "z.json").write_text('{"test": 2}')
            with self.assertRaisesRegex(ValueError, "conflict"):
                copy_snapshots(source, dest)
            self.assertFalse((dest / "a.json").exists())
            self.assertEqual((dest / "z.json").read_text(), '{"test": 2}')

    def test_credentials_rejected_in_nested_payloads(self):
        for value in ({"nested": [{"api_key": "synthetic-secret"}]},
                      {"url": "https://serpapi.com/search?api_key=synthetic-secret&x=1"}):
            with self.assertRaises(ValueError):
                reject_credentials(value)
        reject_credentials({"url": "https://serpapi.com/search?api_key=[REDACTED]&x=1"})

    def test_package_excludes_private_files_and_retains_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            real_root = Path(__file__).resolve().parents[1]
            for name in ("findora_data", "notebooks", "app", "sql"):
                shutil.copytree(real_root / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copyfile(real_root / "UPLOAD.md", root / "UPLOAD.md")
            (root / "config").mkdir()
            (root / "config/products.json").write_text(json.dumps([product()]))
            (root / "config/approvals.json").write_text('[]')
            (root / "config/private.json").write_text('{"api_key":"synthetic-secret"}')
            (root / ".env").write_text('SERPAPI_API_KEY=synthetic-secret')
            (root / "data/raw").mkdir(parents=True)
            (root / "data/raw/test.json").write_text(json.dumps(envelope()))
            target = root / "upload.zip"
            manifest = build_package(root, target)
            self.assertEqual(manifest["expected_bronze_candidates"], 1)
            self.assertEqual(manifest["expected_approved_offers"], 0)
            with zipfile.ZipFile(target) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("Findora_B/01_ingest.py", archive.namelist())
                self.assertIn("Findora_B/snapshots/test.json", archive.namelist())
                self.assertFalse(any(".env" in name or "private.json" in name for name in archive.namelist()))
                self.assertNotIn(b"synthetic-secret", b"".join(archive.read(n) for n in archive.namelist()))


if __name__ == "__main__":
    unittest.main()
