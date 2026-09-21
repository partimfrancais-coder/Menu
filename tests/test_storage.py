"""Exercise persistence and isolation against a temporary, disposable database."""
import copy, http.client, importlib.util, json, pathlib, tempfile, threading, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('menu_server',ROOT/'server.py')
server=importlib.util.module_from_spec(spec); spec.loader.exec_module(server)

class StorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        server.DATA=pathlib.Path(cls.temp.name)/'menus.json'
        cls.seed=json.loads((ROOT/'data'/'menus.json').read_text(encoding='utf-8'))
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()
    def setUp(self):
        server.DATA.write_text(json.dumps(self.seed),encoding='utf-8')
    def request(self,method='GET',path='/api/menus',data=None,origin='http://127.0.0.1:8765'):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        conn.request(method,path,body=json.dumps(data) if data else None,headers={'Host':'127.0.0.1:8765','Origin':origin,'Content-Type':'application/json'})
        response=conn.getresponse();raw=response.read();status=response.status;conn.close()
        return status,json.loads(raw) if raw.startswith(b'{') else raw
    def test_edit_persists_and_other_restaurant_is_unchanged(self):
        data=copy.deepcopy(self.seed);data['restaurants'][0]['categories'][0]['items'][0]['price']=77
        status,result=self.request('POST',data=data);self.assertEqual(status,200)
        saved=self.request()[1]
        self.assertEqual(saved['restaurants'][0]['categories'][0]['items'][0]['price'],77)
        self.assertEqual(saved['restaurants'][1],self.seed['restaurants'][1])
        self.assertEqual(result['revision'],self.seed['revision']+1)
        self.assertTrue(server.DATA.with_suffix('.previous.json').exists())
    def test_restaurant_download_and_replace(self):
        rid=self.seed['restaurants'][0]['id'];path=f'/api/restaurants/{rid}/data'
        status,download=self.request(path=path);self.assertEqual(status,200)
        download['restaurant']['categories']=[]
        status,saved=self.request('POST',path,{'revision':self.seed['revision'],'upload':download})
        self.assertEqual(status,200)
        self.assertEqual(saved['restaurants'][0]['categories'],[])
        self.assertEqual(saved['restaurants'][1],self.seed['restaurants'][1])
        self.assertEqual(self.request()[1],saved)
    def test_rejects_stale_tab_without_overwriting(self):
        data=copy.deepcopy(self.seed)
        self.assertEqual(self.request('POST',data=data)[0],200)
        data['restaurants'][0]['name']='Stale overwrite'
        self.assertEqual(self.request('POST',data=data)[0],409)
        self.assertEqual(self.request()[1]['restaurants'][0]['name'],self.seed['restaurants'][0]['name'])
    def test_malformed_backup_leaves_data_untouched(self):
        data=copy.deepcopy(self.seed);data['restaurants'][0]['categories'][0]['items'][0]['price']=-1
        self.assertEqual(self.request('POST',data=data)[0],400)
        self.assertEqual(self.request()[1],self.seed)
    def test_duplicate_ids_rejected(self):
        data=copy.deepcopy(self.seed);data['restaurants'].append(copy.deepcopy(data['restaurants'][0]))
        self.assertEqual(self.request('POST',data=data)[0],400)
    def test_backup_roundtrip_with_options_and_image(self):
        data=copy.deepcopy(self.seed);i=data['restaurants'][0]['categories'][0]['items'][0]
        i['options']=[dict(name='Large',price=110,kind='Variant'),dict(name='Extra bread',price=15,kind='Add-on')]
        i['image']='data:image/png;base64,iVBORw0KGgo='
        i['reviewed']=True;i['available']=False
        self.assertEqual(self.request('POST',data=data)[0],200)
        self.assertEqual(self.request()[1]['restaurants'][0]['categories'][0]['items'][0],i)
    def test_external_write_blocked(self):
        self.assertEqual(self.request('POST',data=self.seed,origin='https://example.com')[0],403)
    def test_private_data_not_served_as_static_files(self):
        for path in ['/data/menus.json','/../server.py','/sources/../server.py']:
            self.assertEqual(self.request(path=path)[0],404)
    def test_sources_and_static_assets_available(self):
        for path in ['/','/app.js','/styles.css','/sources/Kemang%20Lunch%20%26%20Dinner%2020260605A.pdf','/sources/Kuningan%20Lunch%20%26%20Dinner%2020260606A.pdf']:
            self.assertEqual(self.request(path=path)[0],200)

if __name__=='__main__': unittest.main()
