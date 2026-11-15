"""Findora HTTP contract: explicit demo mode or read-only Databricks mode."""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .sample_data import PRODUCTS, OFFERS, HISTORY, SIMILAR
from .gold import Gold, DataUnavailable
from .service import eligible, advise
from .discovery import Discovery, catalog_matches


def create_app(store=None, mode=None, discovery=None):
    mode = mode or os.getenv('FINDORA_DATA_MODE', 'demo')
    if mode not in ('demo', 'databricks'):
        raise ValueError('FINDORA_DATA_MODE must be demo or databricks')
    store = store or (Gold() if mode == 'databricks' else None)
    app = FastAPI(title='Findora API', version='0.3.0')
    discovery = discovery if discovery is not None else Discovery()
    origins = [s.strip() for s in os.getenv('FINDORA_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if s.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=['GET'], allow_headers=['*'])

    @app.exception_handler(DataUnavailable)
    async def unavailable(request, exc):
        return JSONResponse(status_code=503, content={'detail': 'Databricks data is unavailable; retry later.'})

    @app.get('/health')
    def health():
        if store:
            store.health()
        return {'status': 'ok', 'data_mode': 'observed' if store else 'demo'}

    @app.get('/discover')
    def discover(q: str = Query(..., min_length=2, max_length=500)):
        # External results never enter reviewed Gold offers or buying advice.
        result = discovery.search(q)
        try:
            catalog = store.products() if store else list(PRODUCTS.values())
            matches, similar = catalog_matches(' '.join(result['interpreted']['terms']), catalog)
            result = {**result, 'catalog_matches': matches, 'similar': similar}
        except DataUnavailable:
            result = {**result, 'notices': result['notices'] +
                      ['Reviewed catalog temporarily unavailable; shopping candidates are unverified.']}
        return result

    @app.get('/products/search')
    def search(q: str = Query('', max_length=200)):
        return {'items': store.products(query=q) if store else [p for p in PRODUCTS.values() if q.lower() in (p['title']+' '+p['brand']).lower()]}

    @app.get('/products/{product_id}')
    def product(product_id: str):
        rows = store.products(product_id=product_id) if store else ([PRODUCTS[product_id]] if product_id in PRODUCTS else [])
        if not rows:
            raise HTTPException(404, 'Unknown product')
        return rows[0]

    def observed(p, current=False):
        return eligible(store.observations(p, current=current), demo=p['data_status']=='demo', current=current)

    @app.get('/products/{product_id}/offers')
    def offers(product_id: str):
        p = product(product_id)
        return {'product_id': product_id, 'offers': observed(p, True) if store else OFFERS.get(product_id, [])}

    @app.get('/products/{product_id}/history')
    def history(product_id: str):
        p = product(product_id)
        rows = observed(p) if store else HISTORY.get(product_id, [])
        keys = ('observed_at', 'price', 'currency', 'retailer', 'source_type')
        return {'product_id': product_id, 'observations': [{k:r[k] for k in keys} for r in rows],
                'data_status': 'demo' if p['data_status']=='demo' else ('observed' if rows else 'insufficient')}

    @app.get('/products/{product_id}/similar')
    def similar(product_id: str):
        p = product(product_id)
        if not store:
            return {'product_id': product_id, 'items': SIMILAR.get(product_id, [])}
        # Category alternatives, not exact variants; never invent an unavailable price.
        options = [r for r in store.products() if r['product_id'] != product_id and r['category'] == p['category']
                   and (r['data_status']=='demo') == (p['data_status']=='demo')]
        options.sort(key=lambda r: (r['brand'] != p['brand'], r['title']))
        items = []
        for r in options[:2]:
            fresh = observed(r, True)
            items.append({k:r[k] for k in ('product_id','title','brand')} | {'price': min((o['price'] for o in fresh), default=None),
                         'reason': 'Same category' + (' and brand' if r['brand']==p['brand'] else '') + '; an alternative, not an exact variant match.'})
        return {'product_id': product_id, 'items': items}

    @app.get('/products/{product_id}/advice')
    def advice(product_id: str):
        p = product(product_id)
        return advise(p, observed(p), observed(p, True)) if store else advise(p, [], [])

    return app


app = create_app()
