"""Synthetic inputs test API safety; they are never published as observed prices."""
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.gold import Gold, DataUnavailable
from app.main import create_app
from app.service import eligible, advise

NOW = datetime.now(timezone.utc)
PRODUCT = dict(product_id='test', title='Test clothing', brand='Test', category='sweatshirt', image_url=None, description=None, data_status='observed')


def row(price=100, hours=0, **changes):
    return dict(offer_id=str(hours), retailer='Test retailer', price=price, currency='USD', url='https://example.com/test',
                observed_at=NOW-timedelta(hours=hours), match_type='exact', source_type='snapshot') | changes


class Store:
    def __init__(self, rows=None, status='observed'):
        self.rows = rows or []
        self.p = PRODUCT | {'data_status':status}
    def health(self):
        pass
    def products(self, query='', product_id=None):
        return [dict(self.p)] if product_id in (None,'test') else []
    def observations(self, product, current=False):
        return self.rows


def client(rows=None, status='observed'):
    return TestClient(create_app(Store(rows, status), mode='databricks'))


@pytest.mark.parametrize('changes', [{'price':None},{'price':0},{'price':float('nan')},{'price':float('inf')},
    {'price':True},{'match_type':'revoked'},{'match_type':'unverified'},{'source_type':'demo'},
    {'source_type':'unlabeled'},{'currency':'CAD'},{'observed_at':NOW+timedelta(hours=2)}])
def test_invalid_rows_never_price_real_products(changes):
    assert client([row(**changes)]).get('/products/test/offers').json()['offers']==[]


def test_freshness_history_and_latest_retailer():
    c=client([row(10,0),row(11,1),row(12,25)])
    assert [r['price'] for r in c.get('/products/test/offers').json()['offers']]==[10]
    assert len(c.get('/products/test/history').json()['observations'])==3


def test_exact_24h_boundary():
    assert len(eligible([row(hours=24)], current=True, now=NOW))==1
    assert eligible([row(hours=24.001)], current=True, now=NOW)==[]


def test_no_observations_preserves_null_and_missing_status():
    c=client()
    data=c.get('/products/test/advice').json()
    assert data['decision']=='INSUFFICIENT_DATA'
    assert data['evidence'][0]['current_lowest_price'] is None
    assert data['evidence'][0]['median_observed_price'] is None
    assert data['evidence'][0]['observation_count']==0
    assert c.get('/products/test/history').json()['data_status']=='insufficient'


@pytest.mark.parametrize('price,decision',[(80,'BUY'),(90,'BUY'),(95,'WAIT_OR_COMPARE')])
def test_history_heuristic(price,decision):
    result=advise(PRODUCT,[row(100,72),row(100,48),row(100,24)],[row(price)])
    assert result['decision']==decision
    assert 'not a forecast' in result['explanation']


@pytest.mark.parametrize('history,current', [([row()], [row()]),([row(100,72),row(100,48),row(100,24)],[]),
    ([row(100,1),row(100,2),row(100,3)],[row()])])
def test_insufficient_history_or_no_fresh_price(history,current):
    assert advise(PRODUCT,history,current)['decision']=='INSUFFICIENT_DATA'


def test_demo_history_never_gives_buy_advice():
    c=client([row(100,72,source_type='demo'),row(100,48,source_type='demo'),row(1,source_type='demo')],status='demo')
    assert c.get('/products/test/advice').json()['decision']=='INSUFFICIENT_DATA'
    assert c.get('/products/test/offers').json()['offers'][0]['source_type']=='demo'


def test_revoked_or_demo_history_excluded_for_real():
    c=client([row(1,48,match_type='revoked'), row(1,72,source_type='demo'), row(100)])
    assert len(c.get('/products/test/history').json()['observations'])==1
    assert c.get('/products/test/advice').json()['decision']=='INSUFFICIENT_DATA'


def test_unknown_and_health():
    c=client()
    assert c.get('/products/missing').status_code==404
    assert c.get('/health').json()=={'status':'ok','data_mode':'observed'}
    assert c.get('/products/search').json()['items'][0]['product_id']=='test'


def test_service_outage_does_not_leak_or_fall_back():
    class Broken(Store):
        def health(self):
            raise DataUnavailable('SECRET')
    response=TestClient(create_app(Broken(),mode='databricks')).get('/health')
    assert response.status_code==503
    assert 'SECRET' not in response.text


def test_sql_binding_and_status_translation():
    calls=[]
    def query(sql,params=None):
        calls.append((sql,params))
        return [PRODUCT | {'data_status':'unobserved'}]
    store=Gold(query)
    attack="' OR 1=1 --"
    assert store.products(query=attack)[0]['data_status']=='insufficient'
    assert attack not in calls[0][0]
    assert calls[0][1]=={'query':attack}


def test_invalid_catalog_rejected(monkeypatch):
    monkeypatch.setenv('FINDORA_CATALOG','x; DROP TABLE y')
    with pytest.raises(ValueError):
        Gold()


def test_sql_guardrails_and_params():
    calls=[]
    store=Gold(lambda sql,parameters: calls.append((sql,parameters)) or [])
    store.observations(PRODUCT,current=True)
    sql,params=calls[0]
    assert "match_type = 'exact'" in sql
    assert "source_type IN ('snapshot', 'live')" in sql
    assert 'INTERVAL 24 HOURS' in sql
    assert 'observed_at <= current_timestamp()' in sql
    assert params=={'id':'test'}


def test_single_offer_has_useful_guidance_without_buy_timing():
    result = advise(PRODUCT, [row(220)], [row(220)])
    assert result['decision'] == 'INSUFFICIENT_DATA'
    assert '$220.00 USD' in result['explanation']
    assert 'Test retailer' in result['explanation']
    assert 'still collecting price history' in result['explanation']


def test_columina_typo_preserves_variant_query():
    calls = []
    store = Gold(lambda sql, params: calls.append((sql, params)) or [])
    store.products(query='Columina 2088121 Black')
    assert calls[0][1] == {'query': 'columbia 2088121 Black'}
