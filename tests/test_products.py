import copy,json,unittest
from pathlib import Path
from products import migrate,synchronize,prepare_save,FIELDS
from server import validate,replace_restaurant,restaurant_export

class ProductTests(unittest.TestCase):
 def setUp(self):
  self.old=json.loads(Path('data/menus.json').read_text(encoding='utf-8'))
  a=self.old['restaurants'][0]['categories'][0]['items'][0]
  b=self.old['restaurants'][1]['categories'][0]['items'][0]
  a['productCode']=b['productCode']='SAME';a['price']=10;b['price']=20
  self.data=migrate(self.old)
 def test_priority_and_order_and_idempotence(self):
  validate(self.data)
  self.assertEqual(migrate(self.data),self.data)
  for old,new in zip(self.old['restaurants'],self.data['restaurants']):
   self.assertEqual([(c['id'],[i['id'] for i in c['items']]) for c in old['categories']],[(c['id'],[i['id'] for i in c['items']]) for c in new['categories']])
  rows=[r['categories'][0]['items'][0] for r in self.data['restaurants']]
  self.assertEqual(rows[0]['productId'],rows[1]['productId'])
  self.assertEqual(rows[0]['price'],20)
 def test_global_edits_and_local_visibility(self):
  a,b=[r['categories'][0]['items'][0] for r in self.data['restaurants']]
  a['available']=False
  p=next(p for p in self.data['products'] if p['id']==a['productId'])
  p.update(name='Edited shared dish',price=123,productCode='NEW-001',tags=['Spicy'])
  validate(self.data)
  self.assertEqual(a['price'],123);self.assertEqual(b['name'],p['name'])
  self.assertFalse(a['available']);self.assertTrue(b['available'])
 def test_unknown_reference_and_in_use_deletion_rejected(self):
  pid=self.data['restaurants'][0]['categories'][0]['items'][0]['productId']
  self.data['products']=[p for p in self.data['products'] if p['id']!=pid]
  with self.assertRaises(ValueError):validate(self.data)
 def test_duplicate_codes_rejected(self):
  self.data['products'][1]['productCode']='same'
  with self.assertRaises(ValueError):validate(self.data)
 def test_import_only_existing_and_ignores_local_product_edits(self):
  self.data['revision']=4;r=self.data['restaurants'][0];upload=restaurant_export(self.data,r['id'])
  upload['restaurant']['categories'][0]['items'][0]['price']=999
  result=replace_restaurant(self.data,r['id'],upload)
  self.assertEqual(result['restaurants'][0]['categories'][0]['items'][0]['price'],20)
  self.assertEqual(result['restaurants'][1],self.data['restaurants'][1])
  upload['restaurant']['categories'][0]['items'][0].update(productId='unknown',productCode='unknown')
  with self.assertRaises(ValueError):replace_restaurant(self.data,r['id'],upload)
 def test_stale_schema_rejected(self):
  with self.assertRaises(ValueError):prepare_save(self.old,self.data)

class ProductCategoryTests(ProductTests):
 def categorized(self):
  from products import migrate_categories
  self.data['restaurants'][0]['categories'][0]['name']='Kemang category'
  self.data['restaurants'][1]['categories'][0]['name']='Kuningan category'
  return migrate_categories(self.data)
 def test_one_category_and_priority_with_no_lost_placements(self):
  before={r['id']:{i['id'] for c in r['categories'] for i in c['items']} for r in self.data['restaurants']}
  d=self.categorized();validate(d);products={p['id']:p for p in d['products']};categories={c['id']:c for c in d['productCategories']}
  p=next(p for p in d['products'] if p['productCode']=='SAME')
  self.assertEqual(categories[p['categoryId']]['name'],'Kuningan category')
  for r in d['restaurants']:
   self.assertEqual(before[r['id']],{i['id'] for c in r['categories'] for i in c['items']})
   for c in r['categories']:
    for i in c['items']:self.assertEqual(products[i['productId']]['categoryId'],c['catalogCategoryId'])
 def test_change_category_moves_all_placements_and_rename_is_shared(self):
  d=self.categorized();p=next(p for p in d['products'] if p['productCode']=='SAME');destination=next(c for c in d['productCategories'] if c['id']!=p['categoryId']);p['categoryId']=destination['id'];destination['name']='Renamed category'
  validate(d)
  for r in d['restaurants']:
   c=next(c for c in r['categories'] if any(i['productId']==p['id'] for i in c['items']))
   self.assertEqual(c['catalogCategoryId'],destination['id']);self.assertEqual(c['name'],'Renamed category')
 def test_missing_category_rejected(self):
  d=self.categorized();d['products'][0]['categoryId']='unknown'
  with self.assertRaises(ValueError):validate(d)
 def test_legacy_schema_save_rejected(self):
  d=self.categorized()
  with self.assertRaises(ValueError):prepare_save(self.data,d)
 def test_import_cannot_override_product_category(self):
  d=self.categorized();d['revision']=1;r=d['restaurants'][0];upload=restaurant_export(d,r['id']);source=next(c for c in upload['restaurant']['categories'] if c['items']);i=source['items'].pop();destination=next(c for c in upload['restaurant']['categories'] if c['id']!=source['id']);destination['items'].append(i)
  result=replace_restaurant(d,r['id'],upload);r=result['restaurants'][0];actual=next(c for c in r['categories'] if any(x['id']==i['id'] for x in c['items']));self.assertEqual(actual['catalogCategoryId'],source['catalogCategoryId'])
