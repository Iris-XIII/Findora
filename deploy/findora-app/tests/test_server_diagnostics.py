"""Tests for the temporary DataUnavailable diagnostics in deploy/findora-app/server.py.

Run from the repo root (stdlib unittest; needs fastapi + httpx):
    python3 -m unittest discover -s deploy/findora-app/tests -v

No network, no Databricks: fake `databricks.sql` / `databricks.sdk.core` modules are injected so
the real backend/app/gold.py code path runs and fails with controlled exceptions. Every fake
secret below is a made-up sentinel string, never a real credential.
"""
import importlib.util
import logging
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
LOGGER = "uvicorn.error.findora"

FAKE_TOKEN = "dapiFAKESENTINELTOKEN0123456789abcdef"
FAKE_JWT = "eyJhbGciOiJGQUtFIn0.eyJzdWIiOiJzZW50aW5lbCJ9.c2lnbmF0dXJlU0VOVElORUw"
FAKE_SECRET = "doseFAKECLIENTSECRETSENTINEL"
FAKE_CLIENT_ID = "11111111-2222-3333-4444-fakeclientid"
FAKE_HOST = "dbc-fakesentinelhost.cloud.databricks.com"
FAKE_WAREHOUSE = "fakewarehouse4011403"
SENSITIVE = (FAKE_TOKEN, FAKE_JWT, FAKE_SECRET, FAKE_CLIENT_ID, FAKE_HOST, FAKE_WAREHOUSE,
             "/sql/1.0/warehouses", "Bearer", "SELECT", "product_catalog", "findora_hackathon",
             "Authorization", "https://")
EXPECTED_503 = {"detail": "Databricks data is unavailable; retry later."}


class FakeConfig:
    def __init__(self):
        self.host = f"https://{FAKE_HOST}"

    def authenticate(self):
        return {"Authorization": f"Bearer {FAKE_JWT}"}


class FakeSql(types.ModuleType):
    """Stands in for databricks.sql; connect() raises whatever the test configured."""
    error = None

    def connect(self, **kwargs):
        headers = kwargs["credentials_provider"]()()  # exercise the real credentials wiring
        assert headers["Authorization"].startswith("Bearer ")
        raise self.error


def leaky(cls, text):
    """An exception whose message carries every sentinel, as a careless library might."""
    return cls(f"{text} host={FAKE_HOST} path=/sql/1.0/warehouses/{FAKE_WAREHOUSE} "
               f"Authorization: Bearer {FAKE_JWT} token={FAKE_TOKEN} client_secret={FAKE_SECRET} "
               f"client_id={FAKE_CLIENT_ID} sql=SELECT product_id FROM findora_hackathon.gold.product_catalog")


# Exception classes named like the real connector/SDK ones (classification also uses class names).
class ServerOperationError(Exception):
    pass


class RequestError(Exception):
    pass


class Unauthenticated(Exception):
    pass


class MaxRetryDurationError(RequestError):
    pass


def load_server():
    """Import server.py fresh in databricks mode with a temporary static dir and fake libraries."""
    static = tempfile.mkdtemp(prefix="findora-static-")
    Path(static, "index.html").write_text("<!doctype html><title>Findora test</title>", encoding="utf-8")
    env = {"FINDORA_DATA_MODE": "databricks", "FINDORA_STATIC_DIR": static,
           "DATABRICKS_WAREHOUSE_ID": FAKE_WAREHOUSE, "DATABRICKS_HOST": FAKE_HOST,
           "DATABRICKS_CLIENT_ID": FAKE_CLIENT_ID, "DATABRICKS_CLIENT_SECRET": FAKE_SECRET}
    for name in [m for m in sys.modules if m == "backend" or m.startswith("backend.")]:
        del sys.modules[name]
    os.environ.pop("DATABRICKS_HTTP_PATH", None)
    os.environ.update(env)
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("findora_server_under_test", APP_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DiagnosticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = dict(os.environ)
        cls.fake_sql = FakeSql("databricks.sql")
        sdk_core = types.ModuleType("databricks.sdk.core")
        sdk_core.Config = FakeConfig
        sdk = types.ModuleType("databricks.sdk")
        sdk.core = sdk_core
        root = types.ModuleType("databricks")
        root.__path__ = []
        root.sql, root.sdk = cls.fake_sql, sdk
        cls.fake_modules = {"databricks": root, "databricks.sql": cls.fake_sql,
                            "databricks.sdk": sdk, "databricks.sdk.core": sdk_core}
        cls._saved_modules = {k: sys.modules.get(k) for k in cls.fake_modules}
        sys.modules.update(cls.fake_modules)
        cls.server = load_server()
        from fastapi.testclient import TestClient
        cls.client = TestClient(cls.server.app)

    @classmethod
    def tearDownClass(cls):
        for name, module in cls._saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        os.environ.clear()
        os.environ.update(cls._env)

    def setUp(self):
        sys.modules.update(self.fake_modules)
        os.environ["DATABRICKS_HTTP_PATH"] = f"/sql/1.0/warehouses/{FAKE_WAREHOUSE}"
        os.environ["DATABRICKS_WAREHOUSE_ID"] = FAKE_WAREHOUSE

    def request_logged(self, path, error):
        self.fake_sql.error = error
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            response = self.client.get(path)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), EXPECTED_503)
        output = "\n".join(logs.output)
        for value in SENSITIVE:
            self.assertNotIn(value, output, f"sensitive value leaked into diagnostics: {value!r}")
        return output

    # --- end to end through the real backend/app/gold.py ------------------------------------
    def test_server_derived_http_path_and_startup_flags(self):
        self.assertEqual(os.environ.get("FINDORA_DATA_MODE"), "databricks")
        self.assertEqual(self.server.config_flags(), {"DATABRICKS_HTTP_PATH": True, "DATABRICKS_WAREHOUSE_ID": True})

    def test_permission_denied_on_health(self):
        out = self.request_logged("/health", leaky(ServerOperationError, "[INSUFFICIENT_PERMISSIONS] denied"))
        self.assertIn("category=permission_denied", out)
        self.assertIn("marker=PERMISSION_DENIED", out)
        self.assertIn("ServerOperationError", out)
        self.assertIn("http_path_configured=True warehouse_id_configured=True", out)

    def test_missing_table_on_search(self):
        out = self.request_logged("/products/search?q=parka", leaky(ServerOperationError, "[TABLE_OR_VIEW_NOT_FOUND] x"))
        self.assertIn("category=missing_table marker=TABLE_OR_VIEW_NOT_FOUND", out)

    def test_unsupported_session_configuration(self):
        out = self.request_logged("/health", leaky(ServerOperationError, "[CONFIG_NOT_AVAILABLE] Configuration x"))
        self.assertIn("category=unsupported_sql_configuration", out)

    def test_http_401_and_403(self):
        out = self.request_logged("/health", leaky(RequestError, "Received 401 - UNAUTHORIZED."))
        self.assertIn("category=authentication_failure marker=HTTP_401", out)
        out = self.request_logged("/health", leaky(RequestError, "Error during request: 403 Forbidden"))
        self.assertIn("category=permission_denied marker=HTTP_403", out)

    def test_digits_inside_identifiers_do_not_match_status_codes(self):
        # FAKE_WAREHOUSE contains "401" and "403"; it must not be read as an HTTP status.
        out = self.request_logged("/health", leaky(RuntimeError, "something odd"))
        self.assertIn("category=unknown marker=NONE", out)

    def test_auth_class_and_network_class(self):
        out = self.request_logged("/health", Unauthenticated("no"))
        self.assertIn("category=authentication_failure", out)
        out = self.request_logged("/health", leaky(MaxRetryDurationError, "gave up"))
        self.assertIn("category=connection_failure", out)
        out = self.request_logged("/health", leaky(ConnectionRefusedError, "Connection refused"))
        self.assertIn("category=connection_failure", out)

    def test_missing_http_path_is_missing_configuration(self):
        del os.environ["DATABRICKS_HTTP_PATH"]
        del os.environ["DATABRICKS_WAREHOUSE_ID"]
        out = self.request_logged("/health", leaky(ServerOperationError, "should not be reached"))
        self.assertIn("category=missing_configuration marker=MISSING_DATABRICKS_HTTP_PATH", out)
        self.assertIn("builtins.KeyError", out)
        self.assertIn("http_path_configured=False warehouse_id_configured=False", out)

    def test_missing_connector_is_missing_dependency(self):
        with mock.patch.dict(sys.modules, {"databricks.sql": None}):
            del self.fake_modules["databricks"].sql
            try:
                out = self.request_logged("/health", RuntimeError("unused"))
            finally:
                self.fake_modules["databricks"].sql = self.fake_sql
        self.assertIn("category=missing_dependency marker=IMPORT_ERROR", out)

    def test_response_matches_backend_handler_exactly(self):
        from backend.app.main import create_app
        from backend.app.gold import DataUnavailable
        from fastapi.testclient import TestClient

        class Failing:
            def health(self):
                raise DataUnavailable("Databricks data is unavailable")

        plain = TestClient(create_app(store=Failing(), mode="databricks")).get("/health")
        self.fake_sql.error = ServerOperationError("PERMISSION_DENIED")
        with self.assertLogs(LOGGER, level="ERROR"):
            ours = self.client.get("/health")
        self.assertEqual((ours.status_code, ours.content, ours.headers["content-type"]),
                         (plain.status_code, plain.content, plain.headers["content-type"]))

    def test_diagnostics_failure_keeps_response(self):
        self.fake_sql.error = ServerOperationError("PERMISSION_DENIED")
        with mock.patch.object(self.server, "diagnose", side_effect=RuntimeError(FAKE_TOKEN)):
            with self.assertLogs(LOGGER, level="ERROR") as logs:
                response = self.client.get("/health")
        self.assertEqual((response.status_code, response.json()), (503, EXPECTED_503))
        self.assertEqual(logs.output, [f"ERROR:{LOGGER}:Databricks data unavailable: diagnostics failed"])

    def test_frontend_still_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Findora test", response.text)

    # --- unit: exception chain handling -----------------------------------------------------
    def test_chain_follows_context_suppressed_by_from_none(self):
        from backend.app.gold import DataUnavailable
        try:
            try:
                try:
                    raise ConnectionResetError("inner")
                except ConnectionResetError as inner:
                    raise ServerOperationError("PERMISSION_DENIED") from inner
            except Exception:
                raise DataUnavailable("x") from None
        except DataUnavailable as exc:
            caught = exc
        self.assertTrue(caught.__suppress_context__)
        chain = self.server.exception_chain(caught)
        self.assertEqual([type(e).__name__ for e in chain], ["ServerOperationError", "ConnectionResetError"])
        info = self.server.diagnose(caught)
        self.assertEqual((info["category"], info["marker"]), ("permission_denied", "PERMISSION_DENIED"))

    def test_chain_handles_cycles_limits_and_empty(self):
        a, b = ValueError("a"), ValueError("b")
        a.__context__, b.__context__ = b, a
        top = RuntimeError("top")
        top.__context__ = a
        self.assertEqual(len(self.server.exception_chain(top)), 2)
        deep = RuntimeError("deep")
        cur = deep
        for _ in range(20):
            cur.__context__ = RuntimeError("n")
            cur = cur.__context__
        self.assertEqual(len(self.server.exception_chain(deep)), self.server.MAX_CHAIN)
        self.assertEqual(self.server.diagnose(RuntimeError("alone"))["marker"], "NO_UNDERLYING_EXCEPTION")

    def test_unknown_key_name_is_not_logged(self):
        self.assertEqual(self.server.classify(KeyError(FAKE_SECRET)), ("missing_configuration", "MISSING_KEY"))

    def test_unprintable_exception(self):
        class Unprintable(Exception):
            def __str__(self):
                raise RuntimeError("boom")
        self.assertEqual(self.server.classify(Unprintable()), ("unknown", "NONE"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    unittest.main()
