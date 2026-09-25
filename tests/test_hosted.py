import copy
import json
from pathlib import Path
import tempfile
import unittest
from werkzeug.security import generate_password_hash
from hosted import create_app

class HostedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash=generate_password_hash('test-password',method='pbkdf2:sha256:600000')
        cls.admin2_password_hash=generate_password_hash('admin2-password',method='pbkdf2:sha256:600000')
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.config=dict(TESTING=True,SECRET_KEY='test-session-secret',PASSWORD_HASH=self.password_hash,DATA_DIR=self.temp.name,PUBLIC_ORIGIN='https://menu.test')
        self.app=create_app(self.config);self.client=self.app.test_client()
    def tearDown(self): self.temp.cleanup()
    def call(self,path,method='GET',**kw):
        return self.client.open(path,method=method,base_url='https://menu.test',headers={'Origin':'https://menu.test'},**kw)
    def login(self): return self.call('/login','POST',data={'username':'admin','password':'test-password'})
    def test_anonymous_cannot_read_or_write_menu(self):
        self.assertEqual(self.call('/').status_code,302)
        self.assertEqual(self.call('/api/menus').status_code,401)
        self.assertEqual(self.call('/api/menus','POST',json={}).status_code,401)
        self.assertEqual(self.call('/health').json,{'status':'ok'})
    def test_login_logout_and_secure_cookie(self):
        response=self.login();self.assertEqual(response.status_code,302)
        cookie=response.headers['Set-Cookie']
        for flag in ['Secure','HttpOnly','SameSite=Lax']: self.assertIn(flag,cookie)
        self.assertEqual(self.call('/api/menus').status_code,200)
        self.call('/logout','POST');self.assertEqual(self.call('/api/menus').status_code,401)
    def test_additional_user_can_login_without_replacing_primary_user(self):
        config=dict(self.config,ADDITIONAL_USERS_JSON=json.dumps({'admin2':self.admin2_password_hash}))
        self.app=create_app(config);self.client=self.app.test_client()
        response=self.call('/login','POST',data={'username':'admin2','password':'admin2-password'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.call('/api/menus').status_code,200)
        self.assertEqual(self.call('/users').status_code,403)
        self.call('/logout','POST')
        self.assertEqual(self.login().status_code,302)
    def test_additional_user_remains_disabled_after_restart(self):
        config=dict(self.config,ADDITIONAL_USERS_JSON=json.dumps({'admin2':self.admin2_password_hash}))
        self.app=create_app(config)
        accounts=self.app.extensions['accounts']
        people,_=accounts.listing()
        owner=next(user for user in people if user['owner'])
        extra=next(user for user in people if user['username']=='admin2')
        accounts.manage(extra['id'],'editor',False,owner['id'])
        self.app=create_app(config);self.client=self.app.test_client()
        self.assertEqual(self.call('/login','POST',data={'username':'admin2','password':'admin2-password'}).status_code,401)
    def test_save_survives_app_restart_without_overwriting_seed(self):
        self.login();data=self.call('/api/menus').json
        untouched=copy.deepcopy(data['restaurants'][1]);pid=data['restaurants'][0]['categories'][0]['items'][0]['productId'];next(p for p in data['products'] if p['id']==pid)['price']=89
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,200)
        self.app=create_app(self.config);self.client=self.app.test_client();self.login()
        restored=self.call('/api/menus').json
        self.assertEqual(restored['restaurants'][0]['categories'][0]['items'][0]['price'],89)
        self.assertEqual(restored['restaurants'][1],untouched)
        self.assertTrue((Path(self.temp.name)/'menus.previous.json').exists())
    def test_origin_and_host_protection(self):
        self.assertEqual(self.call('/login').headers['Referrer-Policy'],'same-origin')
        self.login()
        self.assertEqual(self.client.post('/login',base_url='https://menu.test',headers={'Origin':'null'},data={'username':'admin','password':'test-password'}).status_code,403)
        self.assertEqual(self.client.post('/api/menus',base_url='https://menu.test',headers={'Origin':'https://evil.test'},json={}).status_code,403)
        self.assertEqual(self.client.get('/api/menus',base_url='https://evil.test').status_code,403)
    def test_conflict_and_malformed_restore_do_not_overwrite(self):
        self.login();data=self.call('/api/menus').json
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,200)
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,409)
        bad=copy.deepcopy(data);bad['restaurants'][0]['categories'][0]['items'][0]['price']=-1
        self.assertEqual(self.call('/api/menus','POST',json=bad).status_code,400)
    def test_login_rate_limit_and_wrong_password(self):
        for _ in range(10): self.assertEqual(self.call('/login','POST',data={'username':'admin','password':'wrong'}).status_code,401)
        self.assertEqual(self.login().status_code,429)
    def test_hosted_runtime_and_assets(self):
        self.login();self.assertEqual(self.call('/api/runtime').json,{'hosted':True,'user':{'username':'admin','role':'admin','canManageApiKey':False}})
        for path in ['/','/app.js','/styles.css','/sources/Kemang%20Lunch%20%26%20Dinner%2020260605A.pdf']:
            with self.call(path) as response: self.assertEqual(response.status_code,200)
    def test_missing_auth_configuration_fails_closed(self):
        with self.assertRaises(RuntimeError): create_app(dict(self.config,PASSWORD_HASH=''))
        with self.assertRaises(RuntimeError): create_app(dict(self.config,ADDITIONAL_USERS_JSON='not-json'))
    def test_design_prompt_persists_separately_without_changing_dishes(self):
        self.login();data=self.call('/api/menus').json;before=copy.deepcopy(data)
        data['restaurants'][0]['designPrompt']='Kemang design instructions\nNo generation yet.'
        data['restaurants'][1]['designPrompt']='Kuningan design instructions'
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,200)
        self.app=create_app(self.config);self.client=self.app.test_client();self.login()
        saved=self.call('/api/menus').json
        for i in range(2):
            self.assertEqual(saved['restaurants'][i]['designPrompt'],data['restaurants'][i]['designPrompt'])
            self.assertEqual(saved['restaurants'][i]['categories'],before['restaurants'][i]['categories'])
        saved['restaurants'][0]['designPrompt']=''
        self.assertEqual(self.call('/api/menus','POST',json=saved).status_code,200)
        self.assertEqual(self.call('/api/menus').json['restaurants'][0]['designPrompt'],'')
    def test_invalid_design_prompts_rejected(self):
        self.login();data=self.call('/api/menus').json
        for value in [42,{},'x'*30001]:
            data['restaurants'][0]['designPrompt']=value
            self.assertEqual(self.call('/api/menus','POST',json=data).status_code,400)
    def test_shared_catalog_persists_across_restaurants(self):
        self.login();data=self.call('/api/menus').json;other=copy.deepcopy(data['restaurants'][1])
        data['productTags']=[{'name':'Chef choice','kind':'label','icon':'⭐','iconImage':''},{'name':'With rice','kind':'serving','icon':'','iconImage':'data:image/png;base64,iVBORw0KGgo='}]
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,200)
        self.app=create_app(self.config);self.client=self.app.test_client();self.login()
        saved=self.call('/api/menus').json
        self.assertEqual(saved['restaurants'][0]['tagCatalog'],data['productTags'])
        self.assertEqual(saved['restaurants'][1]['tagCatalog'],data['productTags'])
        self.assertEqual(saved['restaurants'][1]['categories'],other['categories'])
        with self.call('/catalog.js') as response: self.assertEqual(response.status_code,200)
    def test_invalid_catalog_rejected_without_overwriting_menu(self):
        self.login();data=self.call('/api/menus').json;before=copy.deepcopy(data)
        for catalog in [[{'name':'Hot','kind':'label'},{'name':'hot','kind':'serving'}],[{'name':'','kind':'label'}],[{'name':'Hot','kind':'unknown'}],['Hot'],[{'name':'Hot','kind':'label','icon':7}],[{'name':'Hot','kind':'label','iconImage':'data:image/svg+xml;base64,abc'}],[{'name':'Hot','kind':'label','iconImage':'data:image/png;base64,'+'a'*400000}]]:
            data['restaurants'][0]['tagCatalog']=catalog
            self.assertEqual(self.call('/api/menus','POST',json=data).status_code,400)
        self.assertEqual(self.call('/api/menus').json,before)

if __name__=='__main__': unittest.main()
