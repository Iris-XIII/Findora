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
import logging
import os
import re
import sys
from pathlib import Path

from fastapi.responses import JSONResponse
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
from backend.app.gold import DataUnavailable  # noqa: E402

# --- Temporary diagnostics for live 503s ----------------------------------------------
# backend/app/gold.py turns every Databricks failure into DataUnavailable (`from None`),
# and the backend handler logs nothing. The original exception is still reachable via
# __context__, so we classify it here. Only fixed strings from this file are logged:
# class names, a category, an allow-listed marker, and configuration booleans. Raw
# exception messages, URLs, SQL, headers, tokens and environment values are never logged.
DIAG_LOG = logging.getLogger("uvicorn.error.findora")  # inherits uvicorn's log handler
MAX_CHAIN = 6
KNOWN_ENV_KEYS = ("DATABRICKS_HTTP_PATH", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_HOST",
                  "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET")
# (category, marker logged, regex searched case-insensitively; matched text is never logged)
MESSAGE_RULES = tuple((cat, marker, re.compile(pattern, re.IGNORECASE)) for cat, marker, pattern in (
    ("permission_denied", "PERMISSION_DENIED", r"permission_denied|insufficient_permissions|\bdoes not have\b"),
    ("missing_table", "TABLE_OR_VIEW_NOT_FOUND", r"table_or_view_not_found"),
    ("missing_table", "SCHEMA_NOT_FOUND", r"schema_not_found"),
    ("missing_table", "CATALOG_NOT_FOUND", r"catalog_not_found|no_such_catalog"),
    ("unsupported_sql_configuration", "CONFIG_NOT_AVAILABLE", r"config_not_available|invalid_conf"),
    ("authentication_failure", "HTTP_401", r"\b401\b|unauthorized|unauthenticated"),
    ("authentication_failure", "INVALID_CLIENT", r"invalid_client|invalid_grant"),
    ("authentication_failure", "NO_DEFAULT_CREDENTIALS", r"cannot configure default credentials"),
    ("permission_denied", "HTTP_403", r"\b403\b|\bforbidden\b"),
    ("connection_failure", "TIMEOUT", r"timed out|\btimeout\b"),
    ("connection_failure", "NETWORK", r"connection refused|connection reset|name or service not known"
                                      r"|nodename nor servname|max retries|failed to establish"),
))
CLASS_RULES = (
    ("authentication_failure", ("Unauthenticated",)),
    ("permission_denied", ("PermissionDenied",)),
    ("connection_failure", ("ConnectionError", "TimeoutError", "MaxRetryError", "MaxRetryDurationError",
                            "NonRecoverableNetworkError", "ConnectTimeout", "ReadTimeout", "TTransportException")),
)
# When the chain points at several causes, report the most specific one.
PRIORITY = ("missing_dependency", "missing_configuration", "permission_denied", "missing_table",
            "unsupported_sql_configuration", "authentication_failure", "connection_failure", "unknown")


def exception_chain(exc, limit=MAX_CHAIN):
    """Causes behind exc (excluding exc itself), following __cause__ then __context__."""
    chain, seen, cur = [], {id(exc)}, exc.__cause__ or exc.__context__
    while cur is not None and id(cur) not in seen and len(chain) < limit:
        chain.append(cur)
        seen.add(id(cur))
        cur = cur.__cause__ or cur.__context__
    return chain


def classify(exc):
    """Return (category, marker) for one exception, using only fixed strings from this file."""
    if isinstance(exc, ImportError):
        return "missing_dependency", "IMPORT_ERROR"
    if isinstance(exc, KeyError):
        key = exc.args[0] if exc.args else None
        return "missing_configuration", f"MISSING_{key}" if key in KNOWN_ENV_KEYS else "MISSING_KEY"
    names = {cls.__name__ for cls in type(exc).__mro__}
    try:
        text = str(exc)  # searched only; never logged
    except Exception:
        text = ""
    for category, marker, pattern in MESSAGE_RULES:
        if pattern.search(text):
            return category, marker
    for category, classes in CLASS_RULES:
        if names.intersection(classes):
            return category, "CLASS_" + category.upper()
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return "connection_failure", "OS_NETWORK"
    return "unknown", "NONE"


def class_label(exc):
    cls = type(exc)
    return f"{cls.__module__}.{cls.__qualname__}"


def config_flags():
    return {name: bool(os.environ.get(name, "").strip())
            for name in ("DATABRICKS_HTTP_PATH", "DATABRICKS_WAREHOUSE_ID")}


def diagnose(exc):
    chain = exception_chain(exc)
    results = [(class_label(e), *classify(e)) for e in chain]
    if not results:
        return {"category": "unknown", "marker": "NO_UNDERLYING_EXCEPTION", "classes": []}
    category, marker = min(((c, m) for _, c, m in results), key=lambda cm: PRIORITY.index(cm[0]))
    return {"category": category, "marker": marker, "classes": [label for label, _, _ in results]}


def install_data_unavailable_diagnostics(target):
    """Wrap the existing DataUnavailable handler: log a safe diagnosis, then return its response."""
    original = target.exception_handlers.get(DataUnavailable)

    async def handler(request, exc):
        try:
            info = diagnose(exc)
            flags = config_flags()
            DIAG_LOG.error(
                "Databricks data unavailable: category=%s marker=%s chain=%s "
                "http_path_configured=%s warehouse_id_configured=%s",
                info["category"], info["marker"], " <- ".join(info["classes"]) or "none",
                flags["DATABRICKS_HTTP_PATH"], flags["DATABRICKS_WAREHOUSE_ID"])
        except Exception:  # diagnostics must never change the API response
            DIAG_LOG.error("Databricks data unavailable: diagnostics failed")
        if original is not None:
            return await original(request, exc)
        return JSONResponse(status_code=503, content={"detail": "Databricks data is unavailable; retry later."})

    target.add_exception_handler(DataUnavailable, handler)
    return handler


install_data_unavailable_diagnostics(app)
_flags = config_flags()
DIAG_LOG.info("Findora App startup: http_path_configured=%s warehouse_id_configured=%s",
              _flags["DATABRICKS_HTTP_PATH"], _flags["DATABRICKS_WAREHOUSE_ID"])

if not (STATIC_DIR / "index.html").is_file():
    raise RuntimeError(f"Compiled frontend not found at {STATIC_DIR / 'index.html'}; run scripts/build_databricks_app.sh")

# Mounted last: only paths not matched by an API route fall through to the frontend files.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="frontend")
