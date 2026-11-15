"""Known-ASIN refresh/import, preserving selected variants and source conflicts."""
import argparse
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit
from .common import identity, timestamp, utc_now, load_products
from .collect import fetch, load_api_key


def candidate(envelope):
    response=envelope['response']; p=response.get('product_results',{})
    offer=response.get('purchase_options',{}).get('single_offer',{})
    details=response.get('product_details',{})
    meta=response['search_metadata']
    selected={}
    problems=[]
    asin=p.get('asin')
    if asin != envelope['request'].get('asin'): problems.append('requested_asin_mismatch')
    for dimension in p.get('variants',[]):
        items=[v for v in dimension.get('items',[]) if v.get('selected') is True]
        if len(items)==1:
            selected[dimension.get('title')]=items[0].get('name')
            if items[0].get('asin') != asin: problems.append('selected_variant_asin_mismatch')
    price=offer.get('extracted_price')
    valid=isinstance(price,(int,float)) and not isinstance(price,bool) and math.isfinite(price) and price>0
    if not valid: problems.append('missing_or_invalid_price')
    if valid and p.get('extracted_price') != price: problems.append('product_purchase_price_mismatch')
    usd=envelope['request'].get('amazon_domain')=='amazon.com' and str(offer.get('price','')).startswith('$')
    if not usd: problems.append('currency_not_confirmed_usd')
    seller=offer.get('features',{}).get('shipper_seller',{}).get('text')
    if not seller: problems.append('missing_seller')
    if str(offer.get('stock','')).casefold() != 'in stock': problems.append('stock_not_confirmed')
    url=p.get('link_clean') or p.get('link') or ''
    parsed=urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('amazon.com','www.amazon.com') or f'/dp/{asin}' not in parsed.path:
        problems.append('invalid_amazon_variant_url')
    conflicts=[]
    if details.get('asin') and details['asin'] != asin: conflicts.append('details_asin_differs')
    if details.get('special_size') and selected.get('Size') and details['special_size'].casefold()!=selected['Size'].casefold():
        conflicts.append('details_size_differs')
    observed=timestamp(meta['created_at'])
    cid=identity(meta['id'],'amazon_product',asin,url,price)
    evidence={'selected':selected,'selected_asin':asin,'details_asin':details.get('asin'),
              'details_special_size':details.get('special_size'),'model':details.get('item_model_number'),
              'brand':details.get('brand_name'),'stock':offer.get('stock'),'seller':seller,
              'source_conflicts':conflicts}
    provenance={'source':'serpapi','source_type':'snapshot','engine':'amazon_product','search_id':meta['id'],
                'candidate_id':cid,'target_product_id':envelope['target_product_id'],
                'source_observed_at':observed.isoformat(),'fetched_at':envelope['fetched_at'],
                'amazon_evidence':evidence}
    return {'candidate_id':cid,'target_product_id':envelope['target_product_id'],'source_product_id':asin or '',
            'title':p.get('title') or '', 'retailer':seller or '', 'price':float(price) if valid else None,
            'currency':'USD' if usd else None,'product_url':url,'observed_at':observed,
            'batch_id':envelope['batch_id'],'provenance':provenance,'problems':sorted(set(problems))}


def target_issues(row, target):
    evidence=row['provenance']['amazon_evidence']; selected=evidence['selected']
    expected_model=target['model'].casefold(); model=str(evidence.get('model') or '').casefold()
    if target['brand'].casefold()=='gildan' and model=='g'+expected_model: model=expected_model
    aliases={'medium':'m','small':'s','large':'l'}
    size=str(selected.get('Size','')).casefold()
    checks={'brand':str(evidence.get('brand') or '').casefold()==target['brand'].casefold(),
            'model':model==expected_model,'color':str(selected.get('Color','')).casefold()==target['color'].casefold(),
            'size':aliases.get(size,size)==target['size'].casefold(),
            'single_item':str(selected.get('Number of Items',''))=='1'}
    return ['amazon_target_'+k+'_not_confirmed' for k,v in checks.items() if not v]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input',help='Import saved targeted probe without another request')
    group.add_argument('--asin',help='Make exactly one product request, without retries')
    parser.add_argument('--products',default='config/focus_products.json')
    parser.add_argument('--env-file')
    parser.add_argument('--output',default='data/amazon_refresh')
    args=parser.parse_args()
    products=load_products(args.products)
    if len(products)!=1: raise ValueError('Choose one canonical target')
    if args.input:
        raw=json.loads(Path(args.input).read_text()); params=raw['request']; response=raw['response']; fetched=raw['fetched_at']
        if params.get('engine')!='amazon_product': raise ValueError('Expected saved Amazon detail response')
    else:
        if not re.fullmatch('[A-Z0-9]{10}',args.asin): raise ValueError('Invalid ASIN')
        key=load_api_key(args.env_file)
        if not key: raise SystemExit('Configure the private SerpAPI key; no request made.')
        params={'engine':'amazon_product','asin':args.asin,'amazon_domain':'amazon.com'}
        response=fetch(params,key); fetched=utc_now()
    envelope={'format_version':1,'source':'serpapi','source_type':'snapshot','market':'us',
              'batch_id':'amazon-'+response['search_metadata']['id'],'target_product_id':products[0]['product_id'],
              'request':params,'response':response,'fetched_at':fetched}
    from .normalize import normalize
    result=normalize([envelope],products,[])
    cid=result['review'][0]['candidate_id']
    output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
    path=output/f'amazon_{cid}.json'
    if path.exists():
        existing=json.loads(path.read_text())
        if existing['response']!=response or existing['request']!=params or existing['target_product_id']!=envelope['target_product_id']:
            raise ValueError('Existing observation differs; not overwritten')
    else:
        path.write_text(json.dumps(envelope,indent=2)+'\n')
    print('Saved ingestion envelope:',path)
    print('Unapproved review:',json.dumps(result['review'][0],default=str))


if __name__=='__main__': main()
