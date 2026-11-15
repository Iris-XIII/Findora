"""Synthetic retailer fixtures only."""
import json
import tempfile
import unittest
from pathlib import Path
from findora_data.retailer_probe import parse,probe
from findora_data.collect import CollectionError
from findora_data.discovery import assess,detail_tokens

P={'product_id':'test','brand':'Gildan','model':'18000','size':'M','color':'Black',
   'discovery':{'model_aliases':['G18000'],'size_aliases':['Medium'],'exclude_title_terms':['S','XL','custom','18000B']}}
TITLE="Gildan Men's G18000 Black Medium Sweatshirt"

class ProbeTests(unittest.TestCase):
    def test_two_requests_and_secret_redaction(self):
        calls=[]
        def fake(params,key):
            calls.append(params)
            return {'organic_results':[],'api_key':key,'url':'https://serpapi.com?api_key='+key}
        with tempfile.TemporaryDirectory() as d:
            _,r=probe(P,d,'TEST_SECRET',fake)
            self.assertEqual([c['engine'] for c in calls],['amazon','walmart'])
            self.assertEqual(len(r),2)
            for f in Path(d).glob('*.json'): self.assertNotIn('TEST_SECRET',f.read_text())
    def test_failure_does_not_retry_or_discard_other_market(self):
        calls=[]
        def fake(params,key):
            calls.append(params)
            if params['engine']=='amazon': raise CollectionError('SECRET')
            return {'organic_results':[]}
        with tempfile.TemporaryDirectory() as d:
            _,r=probe(P,d,'SECRET',fake)
            self.assertEqual(len(calls),2)
            self.assertEqual([x['status'] for x in r],['request_failed','success'])
    def test_amazon_not_assumed_seller_or_approved(self):
        r=parse({'organic_results':[{'title':TITLE,'asin':'TEST','link':'https://amazon.com/dp/TEST',
                'price':'$10','extracted_price':10}]},'amazon',P)[0]
        self.assertEqual(r['status'],'needs_variant_review')
        self.assertIsNone(r['seller'])
        self.assertFalse(r['approved'])
        self.assertEqual(r['missing_title_attributes'],[])
    def test_walmart_retains_seller_not_minimum_teaser_price(self):
        r=parse({'organic_results':[{'title':TITLE,'seller_name':'Third party','product_page_url':'https://walmart.com/ip/test',
            'primary_offer':{'offer_price':12,'min_price':3,'currency':'USD'},'out_of_stock':True}]},'walmart',P)[0]
        self.assertEqual(r['listed_price'],12)
        self.assertEqual(r['seller'],'Third party')
        self.assertEqual(r['status'],'not_shortlisted')
    def test_wrong_variant_missing_price_and_external_links(self):
        r=parse({'organic_results':[{'title':'Gildan 18000 XL','link':'https://evil.example','extracted_price':float('nan')}]},'amazon',P)[0]
        self.assertEqual(r['status'],'not_shortlisted')
        self.assertIsNone(r['listed_price'])
    def test_ranking_model_boundaries_and_possessive(self):
        self.assertEqual(assess(TITLE,P)['title_conflicts'],[])
        self.assertNotIn('model',assess('Gildan 18000B Black M',P)['title_matches'])
        rows=[{'title':'Gildan 18000 XL','immersive_product_page_token':'bad'},
              {'title':TITLE,'immersive_product_page_token':'good'}]
        self.assertEqual(list(detail_tokens(rows,P)),['good'])
