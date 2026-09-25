import json, shutil
from pathlib import Path
import requests, truststore
root=Path(__file__).resolve().parents[2]
stage=root/'.deployment/drinks-routing-release'
assert not stage.exists()
truststore.inject_into_ssl()
c=json.loads((root/'.deployment/credentials.json').read_text());base=c['url'];s=requests.Session()
r=s.post(base+'/login',data={k:c[k] for k in ('username','password')},headers={'Origin':base},allow_redirects=False,timeout=30);assert r.status_code==302
r=s.get(base+'/api/menus',timeout=30);r.raise_for_status();data=r.json()
(root/'.deployment/before-drinks-routing-release.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
targets={'99b9b1b3-6731-4b93-971d-10a1c4e990a4':'KOI Mahakam Drinks and Cocktail','e5ca8e2c-519c-40d8-86be-1727820c3d47':'KOI Rooftop Drinks and Cocktail'}
for rid,name in targets.items():assert next(r for r in data['restaurants'] if r['id']==rid)['name']==name
# Confirm unchanged deployed front-end assets before packaging the local runtime.
for filename in ['app.js','index.html','styles.css','menu-chat.js']:
    r=s.get(base+('/' if filename=='index.html' else '/'+filename),timeout=30);r.raise_for_status()
    assert r.text.replace('\r\n','\n')==(root/'dist'/filename).read_text(encoding='utf-8').replace('\r\n','\n'), 'Live/local UI differs: '+filename
stage.mkdir()
for name in ['Dockerfile','railway.json','.dockerignore','.railwayignore','requirements.txt','server.py','hosted.py','accounts.py','products.py','public_menu.py','menu_ai.py']:
    shutil.copy2(root/name,stage/name)
for name in ['dist','templates']:
    shutil.copytree(root/name,stage/name)
for name in ['koi-menu-pdf','koi-rooftop-menu-pdf','koi-mahakam-drinks-menu-pdf','koi-rooftop-drinks-menu-pdf']:
    shutil.copytree(root/'ai-skills'/name,stage/'ai-skills'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for path in root.glob('*.pdf'):shutil.copy2(path,stage/path.name)
(stage/'data').mkdir();shutil.copy2(root/'data/menus.json',stage/'data/menus.json')
# Keep Kuningan's prepared but unrequested mapping local to the workspace.
code=(stage/'menu_ai.py').read_text(encoding='utf-8')
branch="    if snapshot.get('id') == KUNINGAN_DRINKS_ID:\n        return 'koi-kuningan-drinks-menu-pdf'\n"
assert code.count(branch)==1
(stage/'menu_ai.py').write_text(code.replace(branch,''),encoding='utf-8')
print(json.dumps({'stage':str(stage),'revision':data['revision'],'targetRestaurants':list(targets.values()),'liveUIUnchanged':True}))
