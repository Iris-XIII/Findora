"""Live-discovery tests use synthetic provider responses; no paid requests."""
from fastapi.testclient import TestClient
from app.discovery import Discovery, interpret_search
from app.main import create_app


def test_url_interpretation_without_fetching_private_urls():
    kind, q, host = interpret_search('https://www.printmood.com/products/sweatshirts/gildan-18000?size=m&color=black&srsltid=secret')
    assert kind == 'url' and host == 'www.printmood.com'
    assert 'gildan' in q and '18000' in q and 'black' in q
    assert 'secret' not in q and 'srsltid' not in q


def test_keyword_and_url_search_are_unverified_and_not_in_gold():
    requests = []
    def fake(query, key):
        requests.append((query, key))
        return {'shopping_results': [
            {'title': 'Gildan Heavy Blend Black M', 'source': 'Shop A', 'extracted_price': 11.99,
             'product_link': 'https://shop.example/item'},
            {'title': 'Different color', 'source': 'Shop B', 'extracted_price': 'oops',
             'link': 'javascript:alert(1)'},
        ]}
    discovery = Discovery(key='private-key', fetcher=fake)
    client = TestClient(create_app(mode='demo', discovery=discovery))
    result = client.get('/discover', params={'q': 'Gildan 18000 black medium sweatshirt'}).json()
    assert len(result['discovered']) == 2
    assert result['discovered'][0]['verification'] == 'unverified'
    assert result['discovered'][0]['listed_price'] == 11.99
    assert result['discovered'][1]['listed_price'] is None
    assert result['discovered'][1]['url'] is None
    assert 'variant_not_verified' in result['discovered'][0]['problems']
    assert 'private-key' not in str(result)
    assert client.get('/products/demo-headphones-a/offers').json()['offers'][0]['source_type'] == 'demo'
    assert len(requests) == 1
    client.get('/discover', params={'q': 'Gildan 18000 black medium sweatshirt'})
    assert len(requests) == 1   # in-memory cache avoids repeat billing


def test_no_key_does_not_call_provider_or_invent_listings():
    d = Discovery(key='', fetcher=lambda *_: (_ for _ in ()).throw(AssertionError('network')))
    client = TestClient(create_app(mode='demo', discovery=d))
    result = client.get('/discover?q=black+jacket').json()
    assert result['discovery_status'] == 'unavailable'
    assert result['discovered'] == []
    assert client.get('/products/search?q=headphones').json()['items']


def test_request_limits_and_provider_error():
    count = []
    def fake(q, k):
        count.append(q)
        return {'shopping_results': []}
    d = Discovery(key='key', fetcher=fake, max_requests=1)
    assert d.search('black hoodie')['discovery_status'] == 'no_results'
    assert d.search('black hoodie')['discovery_status'] == 'cached'
    assert d.search('black sweater')['discovery_status'] == 'budget_exhausted'
    assert count == ['black hoodie']
    broken = Discovery(key='key', fetcher=lambda *_: {'error': 'API key=should-not-leak'})
    assert broken.search('black hoodie')['discovery_status'] == 'unavailable'
    assert 'should-not-leak' not in str(broken.search('black hoodie'))


def test_bad_url_and_validation():
    d = Discovery(key='key', fetcher=lambda *_: (_ for _ in ()).throw(AssertionError('network')))
    assert d.search('https://example.com/')['discovery_status'] == 'insufficient_query'
    client = TestClient(create_app(mode='demo', discovery=d))
    assert client.get('/discover').status_code == 422
    assert client.get('/discover', params={'q': 'x'*501}).status_code == 422


def test_catalog_results_are_kept_even_without_serpapi_key():
    class Catalog:
        def products(self, **kwargs):
            return [
                {'product_id': 'gildan', 'title': 'Gildan 18000 Black Sweatshirt', 'brand': 'Gildan',
                 'category': 'sweatshirt', 'image_url': None, 'description': None, 'data_status': 'observed'},
                {'product_id': 'other', 'title': 'Plain Crewneck Sweatshirt', 'brand': 'Brand B',
                 'category': 'sweatshirt', 'image_url': None, 'description': None, 'data_status': 'insufficient'},
            ]
        def health(self):
            pass
    c = TestClient(create_app(store=Catalog(), mode='databricks', discovery=Discovery(key='')))
    result = c.get('/discover', params={'q': 'Gildan 18000 sweatshirt'}).json()
    assert result['discovery_status'] == 'unavailable'
    assert [p['product_id'] for p in result['catalog_matches']] == ['gildan']
    assert result['similar'][0]['price'] is None
    assert result['similar'][0]['product_id'] == 'other'


def test_pasted_url_uses_product_terms_not_tracker_in_paid_query():
    queries = []
    discovery = Discovery(key='test', fetcher=lambda q, _: queries.append(q) or {'shopping_results': []})
    c = TestClient(create_app(mode='demo', discovery=discovery))
    response = c.get('/discover', params={'q':
        'https://www.printmood.com/products/sweatshirts/gildan-18000?size=m&color=black&srsltid=private'})
    assert response.status_code == 200
    assert 'gildan' in queries[0]
    assert 'black' in queries[0]
    assert 'private' not in queries[0]
    assert response.json()['input_type'] == 'url'


def test_catalog_outage_does_not_hide_available_discovery():
    from app.gold import DataUnavailable
    class Offline:
        def products(self, **kwargs):
            raise DataUnavailable('sensitive warehouse details')
    d = Discovery(key='test', fetcher=lambda *_: {'shopping_results': [
        {'title':'Black Hoodie', 'source':'Example', 'extracted_price':12,
         'link':'https://shop.example/hoodie'}
    ]})
    c = TestClient(create_app(store=Offline(), mode='databricks', discovery=d))
    response = c.get('/discover?q=black+hoodie')
    assert response.status_code == 200
    result = response.json()
    assert len(result['discovered']) == 1
    assert 'sensitive' not in response.text


def test_explicit_non_usd_listing_is_not_misrepresented_as_usd():
    d = Discovery(key='test', fetcher=lambda *_: {'shopping_results': [
        {'title': 'Sweatshirt', 'source': 'EU retailer', 'extracted_price': 20,
         'price': '€20', 'link': 'https://shop.example/sweatshirt'}
    ]})
    record = d.search('black sweatshirt')['discovered'][0]
    assert record['listed_price'] is None
    assert record['currency'] is None
    assert 'non_usd_price' in record['problems']


def test_malformed_and_authenticated_urls_do_not_spend_budget():
    d = Discovery(key='test', fetcher=lambda *_: (_ for _ in ()).throw(AssertionError('network')))
    c = TestClient(create_app(mode='demo', discovery=d))
    for query in ('https://[broken/hoodie', 'https://shop.example:wrong/hoodie',
                  'https://user:password@shop.example/hoodie'):
        response = c.get('/discover', params={'q': query})
        assert response.status_code == 200
        assert response.json()['discovery_status'] == 'insufficient_query'
    assert len(d.calls) == 0


def test_malformed_provider_results_return_notice_not_server_error():
    for results in (None, 3, 'bad', {}):
        d = Discovery(key='test', fetcher=lambda *_, results=results: {'shopping_results': results})
        c = TestClient(create_app(mode='demo', discovery=d))
        response = c.get('/discover?q=black+hoodie')
        assert response.status_code == 200
        assert response.json()['discovery_status'] == 'unavailable'


def test_cache_expires_and_concurrent_searches_share_a_request(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import app.discovery as module
    clock = [100]
    monkeypatch.setattr(module, 'monotonic', lambda: clock[0])
    calls = []
    d = Discovery(key='test', fetcher=lambda q, _: calls.append(q) or {'shopping_results': []})
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(d.search, ['black hoodie'] * 4))
    assert len(calls) == 1
    assert sum(r['discovery_status'] == 'cached' for r in results) == 3
    clock[0] += 601
    d.search('black jacket')
    assert 'black hoodie' not in d.cache


def test_discovery_preserves_columbia_spelling_alias():
    from app.discovery import catalog_matches
    _, query, _ = interpret_search('  Columina   parka  ')
    matches, _ = catalog_matches(query, [dict(product_id='parka', title='Columbia Parka', brand='Columbia')])
    assert query == 'columbia parka'
    assert matches[0]['product_id'] == 'parka'


def test_currency_and_google_hostname_boundaries():
    d = Discovery(key='test', fetcher=lambda *_: {'shopping_results': [
        {'title': 'Hoodie', 'price': 'C$20', 'extracted_price': 20,
         'link': 'https://notgoogle.com/shopping'}]})
    record = d.search('black hoodie')['discovered'][0]
    assert record['listed_price'] is None
    assert record['url_kind'] == 'merchant'
