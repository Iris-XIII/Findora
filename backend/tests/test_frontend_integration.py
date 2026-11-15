"""Regression checks for the frontend merged in main c01c991."""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('FINDORA_CORS_ORIGINS',raising=False)
    return TestClient(create_app(mode='demo'))

@pytest.mark.parametrize('origin',['http://localhost:5173','http://127.0.0.1:5173'])
def test_local_frontend_cors(client,origin):
    response=client.options('/products/search',headers={'Origin':origin,'Access-Control-Request-Method':'GET'})
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']==origin

def test_foreign_origin_not_allowed(client):
    response=client.get('/health',headers={'Origin':'https://unconfigured.example'})
    assert 'access-control-allow-origin' not in response.headers

def test_custom_deployed_origin(monkeypatch):
    monkeypatch.setenv('FINDORA_CORS_ORIGINS','https://frontend.example')
    c=TestClient(create_app(mode='demo'))
    assert c.get('/health',headers={'Origin':'https://frontend.example'}).headers['access-control-allow-origin']=='https://frontend.example'

def test_discovery_falls_back_to_catalog(client):
    assert client.get('/discover?q=headphones').status_code==404
    items=client.get('/products/search?q=headphones').json()['items']
    assert items
    pid=items[0]['product_id']
    for suffix in ['', '/offers','/history','/similar','/advice']:
        assert client.get('/products/'+pid+suffix).status_code==200
    assert client.get('/products/'+pid+'/advice').json()['decision']=='INSUFFICIENT_DATA'

def test_empty_catalog_search_and_error_shapes(client):
    assert client.get('/products/search?q=').json()['items']
    assert client.get('/products/missing').json()=={'detail':'Unknown product'}
    assert client.get('/products/search',params={'q':'x'*201}).status_code==422
