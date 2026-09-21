import re
from pathlib import Path
import time
from test_hosted import HostedTests


class AccountTests(HostedTests):
    def invite(self, email='editor@example.com', role='editor'):
        self.login()
        response=self.call('/users','POST',data={'action':'invite','email':email,'role':role})
        self.assertEqual(response.status_code,200)
        return re.search(r'/invite#([A-Za-z0-9_-]+)',response.text)[1]

    def accept(self, token, password='very-long-user-password'):
        return self.call('/invite','POST',data={'token':token,'password':password})

    def test_owner_migration_and_restart(self):
        self.login()
        store=self.app.extensions['accounts']
        users,_=store.listing();self.assertEqual(len(users),1)
        self.assertTrue(users[0]['owner']);self.assertEqual(users[0]['role'],'admin')
        from hosted import create_app
        self.app=create_app(self.config)
        self.assertEqual(self.app.extensions['accounts'].listing()[0],users)

    def test_invite_editor_single_use_and_privileges(self):
        token=self.invite()
        self.assertEqual(self.accept(token).status_code,302)
        self.assertEqual(self.call('/api/runtime').json['user']['role'],'editor')
        self.assertEqual(self.call('/users').status_code,403)
        self.assertEqual(self.call('/users','POST',data={'action':'invite','email':'bad@example.com','role':'admin'}).status_code,403)
        data=self.call('/api/menus').json
        self.assertEqual(self.call('/api/menus','POST',json=data).status_code,200)
        self.assertEqual(self.accept(token).status_code,400)
        self.assertNotIn(token,Path(self.app.extensions['accounts'].path).read_bytes().decode('latin1'))

    def test_revocation_expiration_reissue_and_password(self):
        token=self.invite()
        self.assertEqual(self.accept(token,'short').status_code,400)
        replacement=self.invite()
        self.assertEqual(self.accept(token).status_code,400)
        store=self.app.extensions['accounts'];pending=store.listing()[1]
        self.call('/users','POST',data={'action':'revoke','id':pending[0]['id']})
        self.assertEqual(self.accept(replacement).status_code,400)
        token=self.invite()
        with store.db() as db:db.execute('UPDATE invites SET expires=?',(int(time.time())-1,))
        self.assertEqual(self.accept(token).status_code,400)

    def test_disable_invalidates_existing_session_and_cannot_disable_owner(self):
        token=self.invite();self.accept(token)
        editor_client=self.client
        self.client=self.app.test_client();self.login()
        store=self.app.extensions['accounts'];users=store.listing()[0]
        editor=next(u for u in users if not u['owner']);owner=next(u for u in users if u['owner'])
        self.assertEqual(self.call('/users','POST',data={'action':'update','id':owner['id'],'role':'editor','active':'0'}).status_code,400)
        self.assertEqual(self.call('/users','POST',data={'action':'update','id':editor['id'],'role':'editor','active':'0'}).status_code,302)
        self.client=editor_client
        self.assertEqual(self.call('/api/menus').status_code,401)

    def test_invite_admin_and_origin_protection(self):
        token=self.invite('admin2@example.com','admin');self.accept(token)
        self.assertEqual(self.call('/users').status_code,200)
        self.assertEqual(self.client.post('/users',base_url='https://menu.test',headers={'Origin':'https://evil.test'},data={'action':'invite'}).status_code,403)
        self.assertEqual(self.call('/users','POST',data={'action':'invite','email':'x@example.com','role':'superuser'}).status_code,400)

    def test_old_shared_session_rejected_and_login_email_case_insensitive(self):
        with self.client.session_transaction() as session:session['authenticated']=True
        self.assertEqual(self.call('/api/menus').status_code,401)
        token=self.invite();self.accept(token);self.call('/logout','POST')
        self.assertEqual(self.call('/login','POST',data={'username':'EDITOR@EXAMPLE.COM','password':'very-long-user-password'}).status_code,302)
