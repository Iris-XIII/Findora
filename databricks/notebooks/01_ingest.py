# Databricks notebook source
# MAGIC %md
# MAGIC # Findora: reviewed SerpAPI snapshots → Bronze → Silver → Gold
# MAGIC Select **Serverless** notebook compute. For a Git clone, run the first code cell,
# MAGIC upload saved JSON responses into the printed Volume path, then **Run All**.
# MAGIC For the direct-upload ZIP, snapshots are included and you can **Run All** immediately.
# MAGIC This notebook does not need an API key.
# MAGIC Keep `catalog=workspace`. Leave `project_root` blank unless automatic discovery fails.

# COMMAND ----------
from pathlib import Path
import json
import sys


def locate_project_root(explicit="", cwd=None, notebook_path=None):
    """Locate sibling code/config files without depending on notebook execution CWD."""
    def workspace_path(value):
        value = str(value).strip()
        if value.startswith("file:"):
            value = value[5:]
        if value.startswith(("/Users/", "/Shared/", "/Repos/")):
            value = "/Workspace" + value
        return Path(value)

    if explicit:
        # An explicit path must not silently select a different checkout from CWD.
        starts = [workspace_path(explicit)]
    else:
        starts = []
        if notebook_path:
            starts.append(workspace_path(notebook_path))
        starts.append(Path(cwd) if cwd is not None else Path.cwd())
    checked = set()
    for start in starts:
        for base in [start, *list(start.parents)[:5]]:
            for candidate in (base, base / "databricks"):
                if candidate in checked:
                    continue
                checked.add(candidate)
                required = ("findora_data/common.py", "findora_data/normalize.py",
                            "findora_data/pipeline.py", "config/products.json", "config/approvals.json")
                if all((candidate / name).is_file() for name in required):
                    return candidate
    return None


dbutils.widgets.text("project_root", "", "Optional path to databricks or Findora_B folder")
dbutils.widgets.text("catalog", "workspace", "Existing Unity Catalog catalog")
root_text = dbutils.widgets.get("project_root").strip()
root = locate_project_root(root_text)
notebook_path = None
if root is None and not root_text:
    # Some runtimes use a driver directory rather than the notebook directory.
    # If context access is restricted, the explicit widget remains available.
    try:
        notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    except Exception:
        pass
    root = locate_project_root(notebook_path=notebook_path)
if root is None:
    print(f"Current working directory: {Path.cwd()}")
    if notebook_path:
        print(f"Notebook workspace path: {notebook_path}")
    raise ValueError(
        "Code folder not found. Open the Git folder on branch codex/databricks-serpapi, "
        "then open databricks/notebooks/01_ingest. Set the project_root widget to the "
        "copied workspace path of its databricks folder (containing findora_data AND config). "
        "A standalone copy of this notebook is not sufficient."
    )
print(f"Using code folder: {root}")
sys.path.insert(0, str(root))
from findora_data.common import load_envelopes, load_products
from findora_data.normalize import normalize
from findora_data.pipeline import persist, setup

catalog = dbutils.widgets.get("catalog").strip()
setup(spark, catalog)
raw_path = f"/Volumes/{catalog}/bronze/serpapi_raw/responses"
Path(raw_path).mkdir(parents=True, exist_ok=True)
print(f"Upload collector JSON files into: {raw_path}")

# COMMAND ----------
# MAGIC %md
# MAGIC The packaged `snapshots/` files are copied into the Volume below.
# MAGIC Keep old responses: they are the observed history.
# MAGIC Edit `config/approvals.json` only after checking each exact product and variant.
# MAGIC An empty approvals list is allowed: Bronze will populate, exact offers will remain empty.

# COMMAND ----------
from findora_data.package_upload import copy_snapshots

if (root / "snapshots").is_dir():
    copied = copy_snapshots(root / "snapshots", Path(raw_path))
    print(f"Copied {copied} new snapshot files into the Volume; identical files were kept.")

if not any(Path(raw_path).glob("*.json")):
    raise ValueError(f"Setup succeeded. Upload your saved data/raw/*.json files into {raw_path}, then Run All again.")

products = load_products(root / "config/products.json")
approvals = json.loads((root / "config/approvals.json").read_text())
normalized = normalize(load_envelopes(raw_path), products, approvals)
print({key: len(value) for key, value in normalized.items()})
counts = persist(spark, catalog, normalized)
print(counts)

# COMMAND ----------
# Inspect candidates separately from verified offers. This table is NOT an exact-match comparison.
review_path = Path(raw_path).parent / "review_queue.generated.json"
review_path.write_text(json.dumps(normalized["review"], indent=2) + "\n")
print(f"Generated review queue: {review_path}")
if not normalized["offers"]:
    print("No exact offers approved yet. Bronze ingestion is useful, but matching is still pending.")
review_rows = [{"product_id": r["product_id"], "title": r["title"], "retailer": r["retailer"],
                "price": r["price"], "review_url": r["review_url"],
                "issues": ", ".join(r["problems"])} for r in normalized["review"]]
display(spark.createDataFrame(review_rows,
    "product_id STRING, title STRING, retailer STRING, price DOUBLE, review_url STRING, issues STRING"))

# COMMAND ----------
display(spark.sql(f"SELECT * FROM `{catalog}`.gold.current_offers ORDER BY product_id, price"))
display(spark.sql(f"SELECT * FROM `{catalog}`.gold.price_summary ORDER BY product_id"))
display(spark.sql(f"SELECT * FROM `{catalog}`.gold.price_coverage ORDER BY product_id"))
# Re-run ingestion on the same archive: counts must remain identical.
