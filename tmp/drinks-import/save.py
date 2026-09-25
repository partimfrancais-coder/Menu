import json,sys
from pathlib import Path
import requests,truststore
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server import validate
truststore.inject_into_ssl()
work=ROOT/'tmp/drinks-import'
before=json.loads((work/'before.json').read_text(encoding='utf-8'))
proposed=json.loads((work/'proposed.json').read_text(encoding='utf-8'))
validate(proposed)
c=json.loads((ROOT/'.deployment/credentials.json').read_text());base=c['url'];s=requests.Session()
r=s.post(base+'/login',data={'username':c['username'],'password':c['password']},headers={'Origin':base},allow_redirects=False,timeout=30)
assert r.status_code==302,'Sign-in failed'
r=s.get(base+'/api/menus',timeout=30);r.raise_for_status()
assert r.json()==before,'Live data changed; rebuild proposal from current data before saving'
backup=ROOT/'.deployment/before-drinks-import-20260924.json'
assert not backup.exists(),'Import backup exists; inspect prior save before retrying'
backup.write_text(json.dumps(before,ensure_ascii=False),encoding='utf-8')
r=s.post(base+'/api/menus',json=proposed,headers={'Origin':base},timeout=60);r.raise_for_status()
revision=r.json()['revision']
r=s.get(base+'/api/menus',timeout=30);r.raise_for_status();saved=r.json()
proposed['revision']=revision
assert saved==proposed,'Readback differs'
validate(saved)
assert saved['restaurants'][:-3]==before['restaurants']
assert saved['products'][:len(before['products'])]==before['products']
products={p['id']:p for p in saved['products']}
for restaurant in saved['restaurants'][-3:]:
    assert restaurant['designPrompt']==''
    for category in restaurant['categories']:
        for item in category['items']:
            assert item['productId'] in products
            assert products[item['productId']]['categoryId']==category['catalogCategoryId']
out=ROOT/'output/data';out.mkdir(parents=True,exist_ok=True)
(out/'menu-studio-with-drinks-20260924.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'drinks-import-audit-20260924.json').write_text((work/'audit.json').read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps(dict(saved=True,revision=revision,restaurants=[r['name'] for r in saved['restaurants'][-3:]],existingRestaurantsUnchanged=True,existingProductsUnchanged=True,allLinksValid=True,designPromptsEmpty=True)))
