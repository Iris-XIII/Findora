"""Regression: Gold opens SQL warehouse sessions without unsupported session settings.

SQL warehouses reject arbitrary Spark confs at session open (live App: CONFIG_NOT_AVAILABLE).
Fake `databricks` modules capture connect() arguments; no network or credentials are used.
"""
import sys
import types

import pytest

from app.gold import Gold, DataUnavailable

FAKE_HOST = 'https://dbc-example.cloud.databricks.com'
FAKE_PATH = '/sql/1.0/warehouses/examplewarehouse'
FAKE_HEADERS = {'Authorization': 'Bearer example-not-a-token'}


class FakeConfig:
    host = FAKE_HOST

    def authenticate(self):
        return dict(FAKE_HEADERS)


class FakeCursor:
    description = [('product_id',)]

    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement, parameters=None):
        self.calls.append(('execute', statement, parameters))

    def fetchall(self):
        return [('sample-product',)]


class FakeConnection(FakeCursor):
    def cursor(self):
        return FakeCursor(self.calls)


@pytest.fixture
def connect_calls(monkeypatch):
    calls = []

    def connect(**kwargs):
        calls.append(('connect', kwargs))
        return FakeConnection(calls)

    sql = types.ModuleType('databricks.sql')
    sql.connect = connect
    core = types.ModuleType('databricks.sdk.core')
    core.Config = FakeConfig
    sdk = types.ModuleType('databricks.sdk')
    sdk.core = core
    root = types.ModuleType('databricks')
    root.__path__ = []
    root.sql, root.sdk = sql, sdk
    for name, module in {'databricks': root, 'databricks.sql': sql,
                         'databricks.sdk': sdk, 'databricks.sdk.core': core}.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv('DATABRICKS_HTTP_PATH', FAKE_PATH)
    return calls


def test_connect_sends_no_session_configuration(connect_calls):
    Gold().health()
    (_, kwargs), (_, statement, parameters) = connect_calls
    assert 'session_configuration' not in kwargs
    assert set(kwargs) == {'server_hostname', 'http_path', 'credentials_provider'}
    # SDK unified auth and the warehouse path are unchanged.
    assert kwargs['server_hostname'] == 'dbc-example.cloud.databricks.com'
    assert kwargs['http_path'] == FAKE_PATH
    assert kwargs['credentials_provider']()() == FAKE_HEADERS
    assert statement == 'SELECT product_id FROM `findora_hackathon`.gold.product_catalog LIMIT 1'
    assert parameters == {}


def test_query_parameters_are_still_bound(connect_calls):
    rows = Gold().query('SELECT product_id FROM t WHERE product_id = :id', {'id': 'sample-product'})
    assert rows == [{'product_id': 'sample-product'}]
    assert connect_calls[-1] == ('execute', 'SELECT product_id FROM t WHERE product_id = :id', {'id': 'sample-product'})


def test_missing_http_path_still_maps_to_data_unavailable(connect_calls, monkeypatch):
    monkeypatch.delenv('DATABRICKS_HTTP_PATH')
    with pytest.raises(DataUnavailable):
        Gold().health()
    assert connect_calls == []
