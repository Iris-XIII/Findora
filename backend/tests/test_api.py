from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_health_is_demo():
    assert client.get('/health').json()['data_mode'] == 'demo'

def test_search_contract():
    response = client.get('/products/search?q=headphones')
    assert response.status_code == 200
    assert len(response.json()['items']) >= 1

def test_offer_source_is_labeled():
    offers = client.get('/products/demo-headphones-a/offers').json()['offers']
    assert all(o['source_type'] == 'demo' for o in offers)

def test_unknown_product():
    assert client.get('/products/missing').status_code == 404
