"""Synthetic fixture: never publish as retailer evidence."""
import copy
import unittest
from findora_data.normalize import normalize,candidates
P={'product_id':'test','title':'Synthetic','brand':'Gildan','model':'18000','color':'Black','size':'M','category':'sweatshirt','condition':'new','currency':'USD'}
def raw():
 return {'format_version':1,'source_type':'snapshot','batch_id':'test','target_product_id':'test','fetched_at':'2026-11-15T14:00:00Z',
 'request':{'engine':'amazon_product','asin':'TESTASIN01','amazon_domain':'amazon.com'},
 'response':{'search_metadata':{'id':'synthetic','status':'Success','created_at':'2026-11-15T13:00:00Z'},
 'product_results':{'asin':'TESTASIN01','title':'Synthetic Gildan G18000','link_clean':'https://www.amazon.com/dp/TESTASIN01/','extracted_price':10,
 'variants':[{'title':k,'items':[{'name':v,'asin':'TESTASIN01','selected':True}]} for k,v in [('Color','Black'),('Size','Medium'),('Number of Items','1')]]},
 'product_details':{'brand_name':'Gildan','item_model_number':'G18000','asin':'OTHERASIN1','special_size':'large'},
 'purchase_options':{'single_offer':{'price':'$10.00','extracted_price':10,'stock':'In Stock','features':{'shipper_seller':{'text':'Test seller'}}}}}}
def approval(r):
 return {'candidate_id':candidates(r)[0]['candidate_id'],'product_id':'test','confirmed':True,
 'confirmed_attributes':{k:P[k] for k in ('brand','model','size','color','condition','currency')},'evidence_url':'https://www.amazon.com/dp/TESTASIN01/',
 'evidence_notes':'Synthetic review only','price_verified':True,'available':True,'reviewed_at':'2026-11-15T15:00:00Z',
 'acknowledged_source_conflicts':['details_asin_differs','details_size_differs']}
class AmazonTests(unittest.TestCase):
 def test_unapproved_has_conflict_evidence(self):
  r=normalize([raw()],[P],[])
  self.assertEqual(len(r['bronze']),1); self.assertEqual(r['offers'],[])
  self.assertEqual(r['review'][0]['amazon_evidence']['selected']['Size'],'Medium')
 def test_explicit_review_and_conflicts(self):
  r=raw(); a=approval(r)
  self.assertEqual(len(normalize([r],[P],[a])['offers']),1)
  a['acknowledged_source_conflicts']=[]
  with self.assertRaisesRegex(ValueError,'conflicts'): normalize([r],[P],[a])
 def test_wrong_selected_variant_not_overridden_by_approval(self):
  for index,value in [(0,'Red'),(1,'Large'),(2,'2')]:
   r=raw(); r['response']['product_results']['variants'][index]['items'][0]['name']=value
   with self.assertRaisesRegex(ValueError,'amazon_target'): normalize([r],[P],[approval(r)])
 def test_stock_seller_and_price_guards(self):
  for key,value in [('stock','Out of Stock'),('extracted_price',None),('features',{}),('price','EUR 10')]:
   r=raw(); r['response']['purchase_options']['single_offer'][key]=value
   with self.assertRaisesRegex(ValueError,'invalid candidate'): normalize([r],[P],[approval(r)])
 def test_variant_asin_must_match(self):
  r=raw(); r['response']['product_results']['variants'][0]['items'][0]['asin']='OTHER'
  with self.assertRaisesRegex(ValueError,'asin_mismatch'): normalize([r],[P],[approval(r)])
 def test_cached_response_stable(self):
  r=raw(); other=copy.deepcopy(r); other['fetched_at']='2026-11-15T16:00:00Z'
  self.assertEqual(len(normalize([r,other],[P],[])['bronze']),1)
