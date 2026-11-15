"""Two-request Amazon/Walmart discovery experiment. Never writes approvals or ingestion inputs."""
import argparse
import json
import math
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .collect import CollectionError, fetch, load_api_key, redact
from .common import load_products, utc_now
from .discovery import assess


def plan(product):
    query = f"{product['brand']} {product['model']} {product['color']} medium crewneck sweatshirt single"
    return [dict(engine='amazon', k=query, amazon_domain='amazon.com'),
            dict(engine='walmart', query=query, walmart_domain='walmart.com')]


def parse(payload, engine, product):
    result = []
    for index, row in enumerate(payload.get('organic_results', [])):
        if engine == 'amazon':
            price = row.get('extracted_price')
            currency = 'USD' if str(row.get('price', '')).startswith('$') else None
            link = row.get('link_clean') or row.get('link')
            source_id = row.get('asin')
            seller = row.get('seller_name')
            stock = row.get('stock')
            unavailable = row.get('no_featured_offers_available') is True
        elif engine == 'walmart':
            offer = row.get('primary_offer') or {}
            price, currency = offer.get('offer_price'), offer.get('currency')
            link = row.get('product_page_url')
            source_id = row.get('us_item_id') or row.get('product_id')
            seller = row.get('seller_name')
            stock = row.get('out_of_stock')
            unavailable = stock is True
        else:
            raise ValueError('Unsupported probe engine')
        valid = isinstance(price, (int,float)) and not isinstance(price,bool) and math.isfinite(price) and price > 0
        try:
            host = urlsplit(link or '').hostname or ''
            expected = 'amazon.com' if engine == 'amazon' else 'walmart.com'
            direct = urlsplit(link or '').scheme == 'https' and (host == expected or host.endswith('.'+expected))
        except ValueError:
            direct = False
        assessment = assess(row.get('title') or '', product)
        reasons = list(assessment['title_conflicts'])
        if 'model' not in assessment['title_matches']: reasons.append('model not established in title')
        if not valid or currency != 'USD': reasons.append('missing valid USD price')
        if not direct: reasons.append('missing marketplace URL')
        if unavailable: reasons.append('unavailable in search response')
        result.append({'engine':engine, 'source_id':source_id, 'source_record_index':index,
                       'search_id':payload.get('search_metadata',{}).get('id'),
                       'source_observed_at':payload.get('search_metadata',{}).get('created_at'),
                       'title':row.get('title'), 'marketplace':expected, 'seller':seller,
                       'listed_price':price if valid else None, 'currency':currency,
                       'product_url':link, 'stock_evidence':stock,
                       'variant_options': row.get('variants', {}).get('options', []) if engine == 'amazon' else row.get('variant_swatches', []),
                       'variant_price_note':'Option links do not inherit the parent search price; size and stock require verification.', **assessment,
                       'status':'not_shortlisted' if reasons else 'needs_variant_review',
                       'issues':reasons, 'approved':False,
                       'requires_verification':['exact model/color/size', 'single new garment', 'seller',
                                                'selected-variant stock and price']})
    return sorted(result,key=lambda r:(bool(r['issues']),-r['score'],r['source_record_index']))


def probe(product, output, key, fetcher=fetch):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    batch=uuid.uuid4().hex
    results=[]
    for params in plan(product):
        engine=params['engine']
        try:
            payload=redact(fetcher(params,key),key)
        except CollectionError:
            results.append({'engine':engine,'status':'request_failed','candidates':[],
                            'note':'No automatic retry; inspect provider dashboard privately.'})
            continue
        envelope={'retailer_probe_version':1,'target_product_id':product['product_id'],
                  'fetched_at':utc_now(),'request':params,'response':payload}
        path=output/f'{batch}_{engine}.json'
        path.write_text(json.dumps(envelope,indent=2)+'\n')
        results.append({'engine':engine,'status':'success','raw_file':str(path),
                        'candidates':parse(payload,engine,product)})
    report=output/f'{batch}_report.json'
    report.write_text(json.dumps(results,indent=2)+'\n')
    return report,results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--products',default='config/focus_products.json')
    parser.add_argument('--output',default='data/retailer_probe')
    parser.add_argument('--env-file')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    products=load_products(args.products)
    if len(products)!=1: raise ValueError('Probe requires exactly one target')
    print('Request ceiling: 2 (one Amazon search and one Walmart search; no retries).')
    if args.dry_run:
        print(json.dumps(plan(products[0]),indent=2))
        return
    key=load_api_key(args.env_file)
    if not key: raise SystemExit('Configure SERPAPI_API_KEY privately; no requests made.')
    path,results=probe(products[0],args.output,key)
    for group in results:
        pending=[r for r in group['candidates'] if r['status']=='needs_variant_review']
        print(f"{group['engine']}: {group['status']}; {len(group['candidates'])} candidates; {len(pending)} shortlisted")
        for row in pending[:3]:
            print(f"  {row['title']} | USD {row['listed_price']} | seller: {row['seller'] or 'unknown'}")
    print(f'Report: {path}. Probe files are NOT ingestion inputs; approvals unchanged.')


if __name__=='__main__':
    main()
