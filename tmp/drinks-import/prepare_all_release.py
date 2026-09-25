from pathlib import Path
import shutil,json,requests,truststore
root=Path(__file__).resolve().parents[2]
old=root/'.deployment/drinks-routing-release'
stage=root/'.deployment/all-drinks-routing-release'
assert not stage.exists()
branch="    if snapshot.get('id') == KUNINGAN_DRINKS_ID:\n        return 'koi-kuningan-drinks-menu-pdf'\n"
code=(root/'menu_ai.py').read_text(encoding='utf-8')
assert code.replace(branch,'')==(old/'menu_ai.py').read_text(encoding='utf-8'),'Unrelated runtime difference'
shutil.copytree(old,stage,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(root/'menu_ai.py',stage/'menu_ai.py')
shutil.copytree(root/'ai-skills/koi-kuningan-drinks-menu-pdf',stage/'ai-skills/koi-kuningan-drinks-menu-pdf',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
truststore.inject_into_ssl()
c=json.loads((root/'.deployment/credentials.json').read_text());s=requests.Session()
r=s.post(c['url']+'/login',data={k:c[k] for k in ('username','password')},headers={'Origin':c['url']},allow_redirects=False,timeout=30);assert r.status_code==302
r=s.get(c['url']+'/api/menus',timeout=30);r.raise_for_status()
(root/'.deployment/before-all-drinks-routing-release.json').write_text(json.dumps(r.json(),ensure_ascii=False),encoding='utf-8')
verify=(root/'.deployment/verify_drinks_routing.py').read_text()
verify=verify.replace('expected={','expected={"b8ae17c2-f1e0-4169-8a95-40f4b9b39cc9":"koi-kuningan-drinks-menu-pdf",').replace('before-drinks-routing-release.json','before-all-drinks-routing-release.json')
(root/'.deployment/verify_all_drinks_routing.py').write_text(verify,encoding='utf-8')
print('Prepared isolated release: Kuningan routing and skill only')
