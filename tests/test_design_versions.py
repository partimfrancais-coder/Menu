import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import fitz
from werkzeug.security import generate_password_hash
from hosted import create_app
from menu_ai import menu_reference


def pdf(label):
    with fitz.open() as document:
        page=document.new_page()
        page.insert_text((40,40),label)
        return document.tobytes()


class FakeResponse:
    def __init__(self, value):self.value=value
    def json(self):return self.value


class FakeDesignClient:
    missing_pdf=False
    def __init__(self,key):self.calls=[];self.input=None
    def upload(self,raw):self.input=raw;return 'file-test'
    def call(self,method,path,**kwargs):
        self.calls.append((method,path))
        if method=='POST' and path=='/responses':return FakeResponse({'id':'response-test','status':'completed','output':[
            {'type':'code_interpreter_call','container_id':'container-test'},
            {'type':'message','content':[{'type':'output_text','text':'Created both design files.',
             'annotations':[{'type':'container_file_citation','filename':'/mnt/data/SKILL.md','container_id':'container-test','file_id':'skill-test'},
                            *([] if type(self).missing_pdf else [{'type':'container_file_citation','filename':'/mnt/data/reference.pdf','container_id':'container-test','file_id':'pdf-test'}])]}]}
        ]})
        return FakeResponse({})
    def download(self,container,file_id):return b'# Revised design\n\nUse the new reference layout and saved menu content.\n' if file_id=='skill-test' else pdf('Version from chat')
    def close(self):pass


class DesignVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.hash=generate_password_hash('test-password',method='pbkdf2:sha256:1000')
        self.app=create_app(dict(TESTING=True,SECRET_KEY='test-secret',PASSWORD_HASH=self.hash,USERNAME='alain',
                                 DATA_DIR=self.temp.name,PUBLIC_ORIGIN='https://menu.test',ADDITIONAL_USERS_JSON={},
                                 AI_CLIENT_FACTORY=FakeDesignClient))
        self.client=self.app.test_client();self.ai=self.app.extensions['menu_ai']
        self.call('/login','POST',data={'username':'alain','password':'test-password'})
        self.data=self.call('/api/menus').json;self.restaurant=self.data['restaurants'][0];self.rid=self.restaurant['id']
        self.base=f'/api/ai/restaurants/{self.rid}'
        self.user=self.app.extensions['accounts'].authenticate('alain','test-password',self.hash)
        self.ai.save_key(self.user,'sk-test-key-never-expose-123456789')
        FakeDesignClient.missing_pdf=False
    def tearDown(self):self.temp.cleanup()
    def call(self,path,method='GET',**kwargs):return self.client.open(path,method=method,base_url='https://menu.test',headers={'Origin':'https://menu.test'},**kwargs)

    def test_v1_is_immutable_and_activation_changes_generation_bundle(self):
        versions=self.call(self.base+'/design-versions').json
        self.assertEqual(versions['activeVersion'],1)
        self.assertEqual([v['label'] for v in versions['versions']],['v1'])
        original=self.ai.design_versions.resolve(self.restaurant,1)
        original_skill=(original['skill']/'SKILL.md').read_bytes();original_pdf=original['reference'].read_bytes()
        self.assertEqual(original_pdf,menu_reference(self.ai.root,self.restaurant).read_bytes())
        new_pdf=pdf('New reference artwork')
        body={'parent':'1','skill':(io.BytesIO(b'# New skill\n\nUse revised headings and this reference.\n'),'SKILL.md'),
              'reference':(io.BytesIO(new_pdf),'reference.pdf')}
        response=self.call(self.base+'/design-versions','POST',data=body,content_type='multipart/form-data')
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(response.json['version'],2)
        self.assertEqual(response.json['activeVersion'],1)
        response=self.call(self.base+'/reference?version=2')
        self.assertEqual(response.data,new_pdf);response.close()
        self.assertEqual((original['skill']/'SKILL.md').read_bytes(),original_skill)
        self.assertEqual(original['reference'].read_bytes(),original_pdf)
        self.assertEqual(self.call(self.base+'/design-versions/2/activate','POST').json['activeVersion'],2)
        with patch('menu_ai.threading.Thread'):
            response=self.call(self.base+'/conversation','POST',json={'mode':'fresh','message':'Generate the menu.',
                'requestId':'test-request-123456789','revision':self.data['revision']})
        self.assertEqual(response.status_code,202,response.json)
        tid=response.json['turns'][-1]['id']
        with zipfile.ZipFile(io.BytesIO(self.ai.bundle(tid)[0])) as archive:
            self.assertEqual(archive.read('reference.pdf'),new_pdf)
            self.assertEqual(archive.read(original['skillName']+'/SKILL.md'),b'# New skill\n\nUse revised headings and this reference.\n')
        self.assertEqual(self.call(self.base+'/design-versions/1/activate','POST').json['activeVersion'],1)
        with zipfile.ZipFile(io.BytesIO(self.ai.bundle(tid)[0])) as archive:
            self.assertEqual(archive.read('reference.pdf'),new_pdf,'Queued generation must retain its selected version')
        self.assertEqual(self.call('/api/menus').json,self.data)

    def test_invalid_pair_and_unknown_version_cannot_activate(self):
        bad={'parent':'1','skill':(io.BytesIO(b'# Skill\nEnough detail to pass length.'),'SKILL.md'),
             'reference':(io.BytesIO(b'not a PDF'),'reference.pdf')}
        response=self.call(self.base+'/design-versions','POST',data=bad,content_type='multipart/form-data')
        self.assertEqual(response.status_code,400)
        self.assertEqual(len(self.call(self.base+'/design-versions').json['versions']),1)
        self.assertEqual(self.call(self.base+'/design-versions/2/activate','POST').status_code,404)
        self.assertEqual(self.call(self.base+'/reference?version=2').status_code,404)
        self.call('/logout','POST')
        self.assertEqual(self.call(self.base+'/design-versions').status_code,401)

    def test_new_restaurant_can_start_with_uploaded_pair(self):
        blank=dict(self.restaurant,id='f'*32,source='')
        with self.assertRaisesRegex(ValueError,'needs a skill and reference'):
            self.ai.design_versions.listing(blank)
        raw=pdf('Blank restaurant reference')
        self.assertEqual(self.ai.design_versions.initialize_from_files(blank,'# Initial skill\n\nFollow the supplied reference PDF.',raw),1)
        self.assertEqual(self.ai.design_versions.listing(blank)['activeVersion'],1)
        self.assertEqual(self.ai.design_versions.resolve(blank)['reference'].read_bytes(),raw)
        with self.assertRaisesRegex(ValueError,'already has v1'):
            self.ai.design_versions.initialize_from_files(blank,'# Initial skill\n\nFollow the supplied reference PDF.',raw)

    def test_chat_creates_complete_inactive_version_and_handles_missing_pair(self):
        with patch('menu_ai.threading.Thread'):
            response=self.call(self.base+'/design-chat','POST',json={'parent':1,'message':'Make the headings bolder.',
                'requestId':'chat-request-123456789'})
        self.assertEqual(response.status_code,202,response.json)
        tid=response.json['turns'][-1]['id']
        self.ai.run_design(tid,self.user['id'],self.restaurant)
        turn=self.call(self.base+'/design-chat').json['turns'][-1]
        self.assertEqual((turn['status'],turn['version']),('completed',2))
        self.assertEqual(self.call(self.base+'/design-versions').json['activeVersion'],1)
        response=self.call(self.base+'/reference?version=2')
        with fitz.open(stream=response.data,filetype='pdf') as reference:
            self.assertIn('Version from chat',reference[0].get_text())
        response.close()
        self.assertEqual(self.call(self.base+'/design-chat','POST',json={'parent':1,'message':'Make the headings bolder.',
            'requestId':'chat-request-123456789'}).json['turns'][-1]['id'],tid)
        FakeDesignClient.missing_pdf=True
        with patch('menu_ai.threading.Thread'):
            response=self.call(self.base+'/design-chat','POST',json={'parent':2,'message':'Try another layout.',
                'requestId':'chat-request-987654321'})
        tid=response.json['turns'][-1]['id'];self.ai.run_design(tid,self.user['id'],self.restaurant)
        turn=self.call(self.base+'/design-chat').json['turns'][-1]
        self.assertEqual(turn['status'],'failed')
        self.assertEqual(len(self.call(self.base+'/design-versions').json['versions']),2)

    def test_adjustment_after_switch_does_not_reuse_another_versions_pdf(self):
        import time
        old_id='a'*32;chat_id='b'*32
        with self.ai.db() as db:
            db.execute('INSERT INTO chats VALUES (?,?,?)',(chat_id,self.user['id'],self.rid))
            db.execute('INSERT INTO turns (id,chat,request_id,created,status,prompt,revision,pages) VALUES (?,?,?,?,?,?,?,?)',
                       (old_id,chat_id,'old-request-123456789',time.time()-5,'completed','Old layout.',self.data['revision'],1))
        folder=self.ai.directory/old_id;folder.mkdir()
        (folder/'generation.json').write_text(json.dumps({'mode':'fresh','designVersion':1}),encoding='utf-8')
        (folder/'menu.pdf').write_bytes(pdf('Previous version PDF'))
        v2=self.ai.design_versions.create(self.restaurant,1,'# Revised layout\n\nUse only the new reference.',pdf('Reference v2'))
        self.ai.design_versions.activate(self.restaurant,v2)
        with patch('menu_ai.threading.Thread'):
            response=self.call(self.base+'/conversation','POST',json={'mode':'adjust','message':'Change the spacing.',
                'requestId':'new-request-123456789','revision':self.data['revision']})
        self.assertEqual(response.status_code,202,response.json)
        tid=response.json['turns'][-1]['id']
        with zipfile.ZipFile(io.BytesIO(self.ai.bundle(tid)[0])) as archive:
            self.assertNotIn('previous.pdf',archive.namelist())
            self.assertEqual(json.loads(archive.read('conversation.json')),[])
            self.assertIn('Reference v2',fitz.open(stream=archive.read('reference.pdf'),filetype='pdf')[0].get_text())


if __name__=='__main__':unittest.main()
