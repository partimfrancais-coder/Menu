import json,urllib.request,urllib.parse,http.cookiejar
from pathlib import Path
c=json.loads(Path('.deployment/credentials.json').read_text());base=c['url'];s=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
s.open(urllib.request.Request(base+'/login',data=urllib.parse.urlencode({k:c[k] for k in ('username','password')}).encode(),headers={'Origin':base}),timeout=30).read()
def get(path):return s.open(base+path,timeout=40).read()
data=json.loads(get('/api/menus'));folder=Path('tmp/kuningan-investigation');folder.mkdir(exist_ok=True)
for rest in data['restaurants']:
 if 'kuningan' not in rest['name'].lower() or 'drink' in rest['name'].lower():continue
 (folder/'current.json').write_text(json.dumps(rest),encoding='utf-8')
 chat=json.loads(get('/api/ai/restaurants/'+rest['id']+'/conversation'));(folder/'chat.json').write_text(json.dumps(chat),encoding='utf-8')
 print(json.dumps({'restaurant':rest['name'],'revision':data['revision'],'turns':[{k:t.get(k) for k in ('id','created','status','revision','pages','warnings')} for t in chat['turns'][-5:]]}))
 latest=next((t for t in reversed(chat['turns']) if t.get('pdf')),None)
 if latest:(folder/'latest.pdf').write_bytes(get(latest['pdf']))
