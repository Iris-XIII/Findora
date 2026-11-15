"""Databricks App entry point: Findora FastAPI API + compiled frontend on one origin.

Packaged by scripts/build_databricks_app.sh together with backend/app/*.py and the
frontend build (static/index.html). Deploy the generated staging folder, not this one.

- Imports the existing FastAPI app from backend/app/main.py unchanged (backend-owned code).
- Derives DATABRICKS_HTTP_PATH from DATABRICKS_WAREHOUSE_ID (the App's `sql-warehouse`
  resource) when no explicit HTTP path is set. The warehouse ID is not a secret.
- Serves the compiled frontend at `/`. API routes are registered first, so /health,
  /products/*, /docs and /openapi.json keep their existing behavior.
- Authentication to Databricks is handled inside the backend by the Databricks SDK
  (the App's service principal); this file reads no tokens or credentials.
"""
import os
import re
import sys
from pathlib import Path

from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
STATIC_DIR = Path(os.environ.get("FINDORA_STATIC_DIR", str(ROOT / "static"))).resolve()


def configure_warehouse_path():
    warehouse = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    if not warehouse or os.environ.get("DATABRICKS_HTTP_PATH", "").strip():
        return
    if not re.fullmatch(r"[A-Za-z0-9]{1,64}", warehouse):
        raise RuntimeError("DATABRICKS_WAREHOUSE_ID has an unexpected format")
    os.environ["DATABRICKS_HTTP_PATH"] = f"/sql/1.0/warehouses/{warehouse}"


configure_warehouse_path()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.main import app  # noqa: E402  (environment must be configured first)

if not (STATIC_DIR / "index.html").is_file():
    raise RuntimeError(f"Compiled frontend not found at {STATIC_DIR / 'index.html'}; run scripts/build_databricks_app.sh")

# Mounted last: only paths not matched by an API route fall through to the frontend files.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="frontend")
