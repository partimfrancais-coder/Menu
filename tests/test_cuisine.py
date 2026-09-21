import copy,json,unittest
from pathlib import Path
from products import migrate,migrate_categories,migrate_cuisines
from server import validate,restaurant_export
class CuisineTests(unittest.TestCase):
 def test_migration_and_export(self):
  old=migrate_categories(migrate(json.loads(Path('data/menus.json').read_text(encoding='utf-8'))));d=migrate_cuisines(old);validate(d)
  self.assertTrue(all(p['cuisine']=='' for p in d['products']))
  p=d['products'][0];p['cuisine']='Asian';validate(d)
  for r in d['restaurants']:
   exported=restaurant_export(d,r['id'])['restaurant']
   for c in exported['categories']:
    for i in c['items']:
     if i['productId']==p['id']:self.assertEqual(i['cuisine'],'Asian')
  self.assertEqual(migrate_cuisines(d),d)
 def test_only_allowed_values(self):
  d=migrate(json.loads(Path('data/menus.json').read_text(encoding='utf-8')))
  for value in ['European','Asian','']:
   d['products'][0]['cuisine']=value;validate(d)
  for value in ['Other',None,42,[]]:
   bad=copy.deepcopy(d);bad['products'][0]['cuisine']=value
   with self.assertRaises(ValueError):validate(bad)
