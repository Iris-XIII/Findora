"""Exercise the notebook bootstrap without requiring Databricks or Spark."""
import ast
import tempfile
import unittest
from pathlib import Path


def load_locator():
    notebook = Path(__file__).resolve().parents[1] / "notebooks/01_ingest.py"
    tree = ast.parse(notebook.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "locate_project_root")
    namespace = {"Path": Path}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(notebook), "exec"), namespace)
    return namespace["locate_project_root"]


class NotebookPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "MadHack_2026"
        self.root = self.repo / "databricks"
        for name in ("findora_data/common.py", "findora_data/normalize.py", "findora_data/pipeline.py",
                     "config/products.json", "config/approvals.json"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")
        self.locate = load_locator()

    def test_git_checkout_root_is_accepted(self):
        self.assertEqual(self.locate(cwd=self.repo), self.root)

    def test_nested_notebook_directory_is_accepted(self):
        self.assertEqual(self.locate(cwd=self.root / "notebooks/nested"), self.root)

    def test_notebook_context_works_with_unrelated_cwd(self):
        self.assertEqual(self.locate(cwd="/unrelated/driver",
                                    notebook_path=self.root / "notebooks/01_ingest"), self.root)

    def test_explicit_notebook_path_is_accepted(self):
        self.assertEqual(self.locate(explicit=self.root / "notebooks/01_ingest", cwd="/unrelated"), self.root)

    def test_invalid_explicit_path_does_not_fall_back_to_another_checkout(self):
        self.assertIsNone(self.locate(explicit="/unrelated/checkout", cwd=self.root))

    def test_standalone_notebook_or_partial_folder_is_not_accepted(self):
        (self.root / "config/products.json").unlink()
        self.assertIsNone(self.locate(cwd=self.root / "notebooks"))


if __name__ == "__main__":
    unittest.main()
