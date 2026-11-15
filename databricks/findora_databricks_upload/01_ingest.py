# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Findora: reviewed SerpAPI snapshots → Bronze → Silver → Gold
# MAGIC Select **Serverless** notebook compute and **Run All**. The direct-upload ZIP
# MAGIC includes saved snapshots; no API key or Git repository is needed for this run.
# MAGIC Keep `catalog=workspace`. Leave `project_root` blank unless automatic discovery fails.

# COMMAND ----------

from pathlib import Path
import json
import sys

dbutils.widgets.text("project_root", "", "Optional path to uploaded Findora_B folder")
dbutils.widgets.text("catalog", "workspace", "Existing Unity Catalog catalog")
root_text = dbutils.widgets.get("project_root").strip()
if root_text:
    root = Path(root_text)
else:
    options = [Path.cwd(), Path.cwd().parent, Path.cwd() / "databricks"]
    root = next((p for p in options if (p / "findora_data").is_dir()), None)
    if root is None:
        raise ValueError("Set project_root to the /Workspace/.../Findora_B folder containing findora_data")
sys.path.insert(0, str(root))
from findora_data.common import load_envelopes, load_products
from findora_data.normalize import normalize
from findora_data.pipeline import persist, setup

catalog = dbutils.widgets.get("catalog").strip()
setup(spark, catalog)
raw_path = f"/Volumes/{catalog}/bronze/serpapi_raw/responses"
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

# COMMAND ----------



# COMMAND ----------

from pathlib import Path
import shutil

volume = Path("/Volumes/workspace/bronze/serpapi_raw")
destination = volume / "responses"
destination.mkdir(parents=True, exist_ok=True)

sources = [
    p for p in volume.glob("*.json")
    if p.name != "review_queue.generated.json"
]

# Check conflicts before copying anything.
for source in sources:
    target = destination / source.name
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise ValueError(f"Different file already exists: {target}")

copied = 0
for source in sources:
    target = destination / source.name
    if not target.exists():
        shutil.copyfile(source, target)
        copied += 1

print("New files copied:", copied)
print("Amazon snapshot exists:",
      (destination / "manual_df2e9a19369b51861c6fbe5a5412cf32.json").exists())