"""Local menu editor. Python standard library only; binds exclusively to loopback."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
import json, os, threading, shutil, time

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'menus.json'
LOCK=threading.Lock()
LIMIT=25*1024*1024

def validate(data):
    if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('restaurants'),list): raise ValueError('Invalid menu backup.')
    if not data['restaurants']: raise ValueError('Keep at least one restaurant.')
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
        if not isinstance(r.get('categories'),list): raise ValueError('Invalid categories.')
        for c in r['categories']:
            identity(c); string(c,'name',True); string(c,'notes')
            if not isinstance(c.get('items'),list): raise ValueError('Invalid items.')
            for i in c['items']:
                identity(i); string(i,'name',True); number(i,'price'); picture(i,'image')
                for k in ['description','notes']: string(i,k)
                for k in ['available','reviewed']:
                    if not isinstance(i.get(k),bool): raise ValueError('Invalid '+k+'.')
                if not isinstance(i.get('tags'),list) or not all(isinstance(t,str) for t in i['tags']): raise ValueError('Invalid labels.')
                if not isinstance(i.get('options'),list): raise ValueError('Invalid options.')
                for o in i['options']:
                    string(o,'name',True); number(o,'price')
                    if o.get('kind') not in ['Variant','Add-on']: raise ValueError('Invalid option type.')

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
        if path=='/api/runtime': return self.result(200,{'hosted':False})
        if path=='/api/menus':
            with LOCK: data=json.loads(DATA.read_text(encoding='utf-8'))
            return self.result(200,data)
        if path.startswith('/sources/'):
            name=unquote(path[len('/sources/'):])
            if name not in ['Kemang Lunch & Dinner 20260605A.pdf','Kuningan Lunch & Dinner 20260606A.pdf']: return self.result(404,{'error':'Source not found.'})
            raw=(ROOT/name).read_bytes(); self.send_response(200); self.send_header('Content-Type','application/pdf'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if path not in ['/','/index.html','/app.js','/styles.css']: return self.result(404,{'error':'Not found.'})
        return super().do_GET()
    def do_POST(self):
        if not self.allowed() or self.headers.get('Origin') not in ['http://127.0.0.1:8765','http://localhost:8765']:
            try: length=int(self.headers.get('Content-Length','0'))
            except ValueError: length=0
            if 0<length<=LIMIT: self.rfile.read(length)
            self.close_connection=True
            return self.result(403,{'error':'Local access only.'})
        if urlparse(self.path).path!='/api/menus': return self.result(404,{'error':'Not found.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=LIMIT: return self.result(413,{'error':'Menu data must be smaller than 25 MB.'})
            data=json.loads(self.rfile.read(length)); validate(data)
            with LOCK:
                old=json.loads(DATA.read_text(encoding='utf-8'))
                if data.get('revision')!=old['revision']: return self.result(409,{'error':'Another window changed the menu. Export your backup, then reload before continuing.'})
                data['revision']=old['revision']+1
                temp=DATA.with_suffix('.tmp'); temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                shutil.copy2(DATA,DATA.with_suffix('.previous.json')); os.replace(temp,DATA)
            self.result(200,{'revision':data['revision']})
        except (ValueError,TypeError,KeyError) as exc: self.result(400,{'error':str(exc)})
        except OSError: self.result(500,{'error':'Could not save to disk. Export a backup and check available disk space.'})

if __name__=='__main__':
    print('Menu Studio: http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
