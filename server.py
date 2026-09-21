"""Local menu editor. Python standard library only; binds exclusively to loopback."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
import copy, json, os, threading, shutil, time
from public_menu import public_menu, public_image
from products import synchronize, migrate, migrate_categories, migrate_cuisines, prepare_save

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'menus.json'
LOCK=threading.Lock()
LIMIT=25*1024*1024

def validate(data):
    if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('restaurants'),list): raise ValueError('Invalid menu backup.')
    if not data['restaurants']: raise ValueError('Keep at least one restaurant.')
    if 'products' in data:
        shell=copy.deepcopy(data['restaurants'][0])
        shell['id']='catalog-validation-restaurant'
        shell['categories']=[{'id':'catalog-validation-category','name':'Products','notes':'','items':copy.deepcopy(data['products'])}]
        shell['tagCatalog']=copy.deepcopy(data.get('productTags',[]))
        validate({'version':1,'restaurants':[shell]})
    ids=set()
    def identity(obj):
        if not isinstance(obj,dict): raise ValueError('Invalid record.')
        value=obj.get('id')
        if not isinstance(value,str) or not value or value in ids: raise ValueError('Record identifiers must be unique.')
        ids.add(value)
    def string(obj,key,required=False):
        val=obj.get(key)
        if not isinstance(val,str) or len(val)>15000000 or (required and not val.strip()): raise ValueError('Invalid '+key+'.')
    def number(obj,key):
        val=obj.get(key)
        if type(val) not in (int,float) or not 0<=val<=1e12: raise ValueError('Invalid '+key+'.')
    def picture(obj,key):
        string(obj,key)
        if obj[key] and not obj[key].startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')): raise ValueError('Unsupported image format.')
    for r in data['restaurants']:
        identity(r)
        for k in ['name','menuTitle','currency']: string(r,k,True)
        for k in ['location','footer','dietaryNote','source']: string(r,k)
        for k in ['priceUnit','serviceCharge','tax']: number(r,k)
        if r['priceUnit']<=0: raise ValueError('Price unit must be positive.')
        picture(r,'logo')
        if 'designPrompt' in r:
            string(r,'designPrompt')
            if len(r['designPrompt'])>30000: raise ValueError('Menu design prompt must be at most 30,000 characters.')
        if 'tagCatalog' in r:
            if not isinstance(r['tagCatalog'],list): raise ValueError('Invalid label catalog.')
            names=set()
            for tag in r['tagCatalog']:
                if not isinstance(tag,dict): raise ValueError('Invalid label definition.')
                string(tag,'name',True)
                if len(tag['name'])>200 or tag.get('kind') not in ('label','serving'): raise ValueError('Invalid label definition.')
                if 'icon' in tag and (not isinstance(tag['icon'],str) or len(tag['icon'])>32): raise ValueError('Invalid label icon.')
                if 'iconImage' in tag:
                    picture(tag,'iconImage')
                    if len(tag['iconImage'])>400000: raise ValueError('Label icon image is too large.')
                name=tag['name'].strip().lower()
                if name in names: raise ValueError('Label names must be unique within a restaurant.')
                names.add(name)
        if not isinstance(r.get('categories'),list): raise ValueError('Invalid categories.')
        for c in r['categories']:
            identity(c); string(c,'name',True); string(c,'notes')
            if not isinstance(c.get('items'),list): raise ValueError('Invalid items.')
            for i in c['items']:
                identity(i); string(i,'name',True); number(i,'price'); picture(i,'image')
                if 'productCode' in i:
                    string(i,'productCode')
                    if len(i['productCode'])>100: raise ValueError('Product code must be at most 100 characters.')
                if i.get('cuisine','') not in ('','European','Asian'): raise ValueError('Cuisine must be European or Asian.')
                for k in ['description','notes']: string(i,k)
                for k in ['available','reviewed']:
                    if not isinstance(i.get(k),bool): raise ValueError('Invalid '+k+'.')
                if not isinstance(i.get('tags'),list) or not all(isinstance(t,str) for t in i['tags']): raise ValueError('Invalid labels.')
                if not isinstance(i.get('options'),list): raise ValueError('Invalid options.')
                for o in i['options']:
                    string(o,'name',True); number(o,'price')
                    if o.get('kind') not in ['Variant','Add-on']: raise ValueError('Invalid option type.')

    synchronize(data)

def restaurant_export(data,rid):
    restaurant=next((r for r in data['restaurants'] if r['id']==rid),None)
    if restaurant is None: raise ValueError('Restaurant not found.')
    return {'format':'menu-studio-restaurant','version':1,'restaurant':copy.deepcopy(restaurant)}

def replace_restaurant(current,rid,upload):
    if not isinstance(upload,dict) or upload.get('format')!='menu-studio-restaurant' or upload.get('version')!=1 or not isinstance(upload.get('restaurant'),dict):
        raise ValueError('Upload a restaurant JSON file downloaded from Manage data.')
    result=copy.deepcopy(current)
    position=next((n for n,r in enumerate(result['restaurants']) if r['id']==rid),None)
    if position is None: raise ValueError('Restaurant not found.')
    replacement=copy.deepcopy(upload['restaurant'])
    replacement['id']=rid
    # Absent optional fields must not resurrect old or default content.
    replacement.setdefault('designPrompt','')
    replacement.setdefault('tagCatalog',[])
    if 'products' in current:
        by_id={p['id']:p for p in current['products']}
        by_code={p.get('productCode','').strip().casefold():p for p in current['products'] if p.get('productCode','').strip()}
        for cat in replacement.get('categories',[]):
            for item in cat.get('items',[]):
                product=by_id.get(item.get('productId')) or by_code.get(str(item.get('productCode','')).strip().casefold())
                if not product: raise ValueError('Upload contains an unknown product. Create it in Products first.')
                item['productId']=product['id']
    result['restaurants'][position]=replacement
    validate(result)
    result['revision']=current['revision']+1
    return result

def write_replacement(path,data):
    raw=json.dumps(data,ensure_ascii=False,indent=2)
    temp=path.with_suffix('.tmp')
    with temp.open('w',encoding='utf-8') as target:
        target.write(raw);target.flush();os.fsync(target.fileno())
    # The automatic previous-file copy must not retain the replaced restaurant.
    previous_temp=path.with_suffix('.previous.tmp')
    previous_temp.write_text(raw,encoding='utf-8')
    os.replace(previous_temp,path.with_suffix('.previous.json'))
    os.replace(temp,path)

class Handler(SimpleHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'dist'),**kw)
    def allowed(self):
        host=self.headers.get('Host','')
        return host in ['127.0.0.1:8765','localhost:8765']
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; object-src 'none'")
        super().end_headers()
    def result(self,status,data):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if not self.allowed(): return self.result(403,{'error':'Local access only.'})
        path=urlparse(self.path).path
        if path.startswith('/api/public/menus/'):
            try:
                with LOCK: current=json.loads(DATA.read_text(encoding='utf-8'))
                parts=path.split('/')
                if len(parts)==7 and parts[5]=='images':
                    raw,mime=public_image(current,unquote(parts[4]),unquote(parts[6]));self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
                return self.result(200,public_menu(current,unquote(path.rsplit('/',1)[-1])))
            except ValueError:return self.result(404,{'error':'Menu not found.'})
        if path.startswith('/menu/'):
            with LOCK: current=json.loads(DATA.read_text(encoding='utf-8'))
            if not any(r['id']==unquote(path.rsplit('/',1)[-1]) for r in current['restaurants']):return self.result(404,{'error':'Menu not found.'})
            self.path='/customer.html';return super().do_GET()
        if path.startswith('/customer/'):
            assets={'/customer/menu.css':'customer.css','/customer/menu.js':'customer.js','/customer/menu-icons.js':'menu-icons.js'}
            if path not in assets:return self.result(404,{'error':'Not found.'})
            self.path='/'+assets[path];return super().do_GET()
        if path=='/api/runtime': return self.result(200,{'hosted':False})
        if path.startswith('/api/restaurants/') and path.endswith('/data'):
            try:
                with LOCK: exported=restaurant_export(json.loads(DATA.read_text(encoding='utf-8')),unquote(path.split('/')[3]))
                return self.result(200,exported)
            except ValueError as exc:return self.result(404,{'error':str(exc)})
        if path=='/api/menus':
            with LOCK: data=json.loads(DATA.read_text(encoding='utf-8'))
            return self.result(200,data)
        if path.startswith('/sources/'):
            name=unquote(path[len('/sources/'):])
            if name not in ['Kemang Lunch & Dinner 20260605A.pdf','Kuningan Lunch & Dinner 20260606A.pdf','MAHAKAM LUNCH DINNER 20260605A.pdf']: return self.result(404,{'error':'Source not found.'})
            raw=(ROOT/name).read_bytes(); self.send_response(200); self.send_header('Content-Type','application/pdf'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if path not in ['/','/index.html','/app.js','/catalog.js','/menu-icons.js','/design-prompts.js','/styles.css']: return self.result(404,{'error':'Not found.'})
        return super().do_GET()
    def do_POST(self):
        if not self.allowed() or self.headers.get('Origin') not in ['http://127.0.0.1:8765','http://localhost:8765']:
            try: length=int(self.headers.get('Content-Length','0'))
            except ValueError: length=0
            if 0<length<=LIMIT: self.rfile.read(length)
            self.close_connection=True
            return self.result(403,{'error':'Local access only.'})
        path=urlparse(self.path).path
        replacing=path.startswith('/api/restaurants/') and path.endswith('/data')
        if path!='/api/menus' and not replacing: return self.result(404,{'error':'Not found.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=LIMIT: return self.result(413,{'error':'Menu data must be smaller than 25 MB.'})
            data=json.loads(self.rfile.read(length))
            if replacing:
                with LOCK:
                    old=json.loads(DATA.read_text(encoding='utf-8'))
                    if not isinstance(data,dict) or data.get('revision')!=old['revision']:return self.result(409,{'error':'Menu changed. Reload before replacing data.'})
                    updated=replace_restaurant(old,unquote(path.split('/')[3]),data.get('upload'))
                    write_replacement(DATA,updated)
                return self.result(200,updated)
            validate(data)
            with LOCK:
                old=json.loads(DATA.read_text(encoding='utf-8'))
                if data.get('revision')!=old['revision']: return self.result(409,{'error':'Another window changed the menu. Export your backup, then reload before continuing.'})
                prepare_save(data,old); validate(data)
                data['revision']=old['revision']+1
                temp=DATA.with_suffix('.tmp'); temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                shutil.copy2(DATA,DATA.with_suffix('.previous.json')); os.replace(temp,DATA)
            self.result(200,{'revision':data['revision']})
        except (ValueError,TypeError,KeyError) as exc: self.result(400,{'error':str(exc)})
        except OSError: self.result(500,{'error':'Could not save to disk. Export a backup and check available disk space.'})

if __name__=='__main__':
    original=json.loads(DATA.read_text(encoding='utf-8'))
    if 'products' not in original or 'productCategories' not in original or any('cuisine' not in p for p in original.get('products',[])):
        updated=migrate_cuisines(migrate_categories(migrate(original))); validate(updated); updated['revision']=original['revision']+1
        shutil.copy2(DATA,DATA.with_suffix('.before-cuisine.json')); write_replacement(DATA,updated)
    print('Menu Studio: http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
