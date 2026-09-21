import copy,json
from pathlib import Path
import test_hosted

class CustomerMenuTests(test_hosted.HostedTests):
 def test_public_menu_is_read_only_and_excludes_private_fields(self):
  self.login();d=self.call('/api/menus').json;r=d['restaurants'][0];rid=r['id'];p=d['products'][0]
  r['designPrompt']='PRIVATE PROMPT';p['notes']='PRIVATE PRODUCT NOTES'
  entry=r['categories'][0]['items'][0];entry['available']=False;hidden_name=entry['name']
  self.assertEqual(self.call('/api/menus','POST',json=d).status_code,200)
  self.call('/logout','POST')
  res=self.call('/api/public/menus/'+rid);self.assertEqual(res.status_code,200)
  self.assertNotIn('PRIVATE',res.text)
  for c in res.json['categories']:
   for item in c['items']:
    self.assertNotIn('notes',item);self.assertNotIn('productCode',item);self.assertNotIn('productId',item);self.assertNotIn('reviewed',item)
  self.assertNotIn(hidden_name,[i['name'] for c in res.json['categories'] for i in c['items']])
  for path in ['/menu/'+rid,'/customer/menu.js','/customer/menu.css','/customer/menu-icons.js']:
   with self.call(path) as response:self.assertEqual(response.status_code,200)
  self.assertEqual(self.call('/api/menus').status_code,401)
  self.assertEqual(self.call('/api/public/menus/'+rid,'POST',json={}).status_code,401)
  self.assertIn(self.call('/customer/../hosted.py').status_code,(302,404))
  self.assertEqual(self.call('/customer/hosted.py').status_code,404)
  self.assertEqual(self.call('/api/public/menus/missing').status_code,404)
  self.assertEqual(self.call('/menu/missing').status_code,404)
 def test_public_payload_visible_images_labels_price_and_options(self):
  self.login();d=self.call('/api/menus').json;r=d['restaurants'][0]
  view=self.call('/api/public/menus/'+r['id']).json
  source=[i for c in r['categories'] for i in c['items'] if i['available']]
  shown=[i for c in view['categories'] for i in c['items']]
  self.assertEqual(len(source),len(shown))
  for a,b in zip(source,shown):
   for k in ['name','image','price','tags','options']:self.assertEqual(a[k],b[k])
 def test_public_images_only_for_visible_items(self):
  self.login();d=self.call('/api/menus').json;r=d['restaurants'][0];i=r['categories'][0]['items'][0];p=next(p for p in d['products'] if p['id']==i['productId']);p['image']='data:image/png;base64,aGVsbG8='
  self.assertEqual(self.call('/api/menus','POST',json=d).status_code,200);self.call('/logout','POST')
  view=self.call('/api/public/menus/'+r['id']).json;url=view['categories'][0]['items'][0]['image'];res=self.call(url);self.assertEqual(res.status_code,200);self.assertEqual(res.data,b'hello');self.assertEqual(res.mimetype,'image/png')
  self.login();d=self.call('/api/menus').json;d['restaurants'][0]['categories'][0]['items'][0]['available']=False;self.assertEqual(self.call('/api/menus','POST',json=d).status_code,200);self.call('/logout','POST');self.assertEqual(self.call(url).status_code,404)
