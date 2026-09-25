import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import fitz
import requests
from werkzeug.security import generate_password_hash

from hosted import create_app
from menu_ai import GenerationError, MODEL, OpenAI, validate_pdf, ROOFTOP_ID, ROOFTOP_INSTRUCTIONS, INSTRUCTIONS, menu_skill
from menu_ai import KUNINGAN_DRINKS_ID, KUNINGAN_DRINKS_INSTRUCTIONS
from menu_ai import MAHAKAM_DRINKS_ID, MAHAKAM_DRINKS_INSTRUCTIONS
from menu_ai import ROOFTOP_DRINKS_ID, ROOFTOP_DRINKS_INSTRUCTIONS


def sample_pdf():
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=420)
        page.insert_text((40, 50), 'KOI - Menu design preview', fontsize=24)
        page.insert_text((40, 100), 'Test dish                         95', fontsize=14)
        page.insert_text((40, 125), 'A fixture used only for integration tests.', fontsize=11)
        return doc.tobytes()


class FakeResponse:
    def __init__(self, value): self.value = value
    def json(self): return self.value


class FakeOpenAI:
    instances = []
    fail = False
    no_pdf = False

    def __init__(self, key):
        self.calls = []; self.uploads = []; self.key = key
        type(self).instances.append(self)

    def upload(self, raw):
        self.uploads.append(raw)
        return 'file-test'

    def call(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if method == 'POST' and path == '/responses':
            if type(self).fail: raise GenerationError('OpenAI usage or rate limit reached.')
            return FakeResponse({'id': 'resp-test', 'status': 'queued'})
        if method == 'GET' and path == '/responses/resp-test':
            refs = [] if type(self).no_pdf else [
                {'type': 'container_file_citation', 'filename': '/mnt/data/menu.pdf', 'container_id': 'cntr-test', 'file_id': 'cfile-pdf'},
                {'type': 'container_file_citation', 'filename': '/mnt/data/source.zip', 'container_id': 'cntr-test', 'file_id': 'cfile-source'},
            ]
            return FakeResponse({'id': 'resp-test', 'status': 'completed', 'output': [
                {'type': 'code_interpreter_call', 'container_id': 'cntr-test'},
                {'type': 'message', 'content': [{'type': 'output_text', 'text': 'Here is [your menu](sandbox:/mnt/data/menu.pdf).', 'annotations': refs}]},
            ]})
        return FakeResponse({})

    def download(self, container, file_id):
        if file_id == 'cfile-pdf': return sample_pdf()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z: z.writestr('renderer.py', '# Editable test fixture')
        return buf.getvalue()

    def close(self): pass


class MenuAITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = generate_password_hash('test-password', method='pbkdf2:sha256:1000')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = dict(TESTING=True, SECRET_KEY='test-session-secret', PASSWORD_HASH=self.password_hash,
                           USERNAME='alain', DATA_DIR=self.temp.name, PUBLIC_ORIGIN='https://menu.test',
                           ADDITIONAL_USERS_JSON={'editor': self.password_hash}, AI_CLIENT_FACTORY=FakeOpenAI)
        self.app = create_app(self.config); self.client = self.app.test_client()
        self.service = self.app.extensions['menu_ai']
        self.call('/login', 'POST', data={'username': 'alain', 'password': 'test-password'})
        self.user = self.app.extensions['accounts'].authenticate('alain', 'test-password', self.password_hash)
        self.data = self.call('/api/menus').json
        self.restaurant = self.data['restaurants'][0]
        self.rid = self.restaurant['id']
        self.url = f'/api/ai/restaurants/{self.rid}/conversation'
        FakeOpenAI.instances = []; FakeOpenAI.fail = FakeOpenAI.no_pdf = False

    def tearDown(self): self.temp.cleanup()

    def call(self, path, method='GET', **kwargs):
        return self.client.open(path, method=method, base_url='https://menu.test', headers={'Origin': 'https://menu.test'}, **kwargs)

    def save_key(self):
        response = self.call('/api/ai/key', 'PUT', json={'key': 'sk-test-key-never-expose-123456789'})
        self.assertEqual(response.status_code, 200)

    def test_design_skill_matches_generation_without_provider_or_menu_changes(self):
        before = self.call('/api/menus').json
        response = self.call(f'/api/ai/restaurants/{self.rid}/design-skill')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        result = response.json
        self.assertEqual(result['skillName'], self.call(self.url).json['pdfSkill'])
        self.assertEqual(result['restaurantName'], self.restaurant['name'])
        self.assertEqual(result['designPrompt'], self.restaurant.get('designPrompt', ''))
        self.assertEqual(result['documents'][0]['name'], 'SKILL.md')
        folder = self.service.root / 'ai-skills' / result['skillName']
        for doc in result['documents']:
            self.assertEqual(doc['content'], (folder / doc['name']).read_text(encoding='utf-8'))
            self.assertTrue(doc['name'].endswith('.md'))
        self.assertEqual(self.call('/api/menus').json, before)
        self.assertEqual(FakeOpenAI.instances, [])

    def test_design_skill_requires_login_and_existing_restaurant(self):
        self.assertEqual(self.call('/api/ai/restaurants/missing/design-skill').status_code, 404)
        self.call('/logout', 'POST')
        self.assertEqual(self.call(f'/api/ai/restaurants/{self.rid}/design-skill').status_code, 401)

    def test_design_skill_reports_missing_bundle(self):
        with patch.object(self.service.design_versions, 'resolve', side_effect=ValueError('The design skill is unavailable.')):
            response = self.call(f'/api/ai/restaurants/{self.rid}/design-skill')
        self.assertEqual(response.status_code, 404)
        self.assertIn('unavailable', response.json['error'])

    def test_reference_view_and_download_match_generation_reference(self):
        from menu_ai import menu_reference
        url = f'/api/ai/restaurants/{self.rid}/reference'
        expected = self.service.design_versions.resolve(self.restaurant)['reference']
        self.assertTrue(expected.is_file())
        metadata = self.call(f'/api/ai/restaurants/{self.rid}/design-skill').json
        self.assertEqual(metadata['reference']['name'], expected.name)
        for suffix, disposition in [('', 'inline'), ('?download=1', 'attachment')]:
            response = self.call(url + suffix)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/pdf')
            self.assertTrue(response.headers['Content-Disposition'].startswith(disposition))
            self.assertEqual(response.data, expected.read_bytes())
            response.close()
        self.assertEqual(self.call('/api/ai/restaurants/missing/reference').status_code, 404)
        self.call('/logout', 'POST')
        self.assertEqual(self.call(url).status_code, 401)

    def test_reference_uses_branch_artwork_and_rejects_arbitrary_sources(self):
        from menu_ai import menu_reference
        for rid, name in [(ROOFTOP_ID, 'rooftop-original.pdf'), (KUNINGAN_DRINKS_ID, 'kuningan-drinks-original.pdf'),
                          (MAHAKAM_DRINKS_ID, 'mahakam-drinks-original.pdf'), (ROOFTOP_DRINKS_ID, 'rooftop-drinks-original.pdf')]:
            reference = menu_reference(self.service.root, dict(self.restaurant, id=rid))
            self.assertEqual(reference.name, name)
            self.assertTrue(reference.is_file())
        self.assertIsNone(menu_reference(self.service.root, {'id': 'new', 'source': '../accounts.py'}))
        self.assertIsNone(menu_reference(self.service.root, {'id': 'new', 'source': ''}))

    def test_missing_reference_is_not_offered(self):
        with patch.object(self.service.design_versions, 'resolve', side_effect=ValueError('The design version is missing its reference PDF.')):
            self.assertEqual(self.call(f'/api/ai/restaurants/{self.rid}/design-skill').status_code, 404)
            self.assertEqual(self.call(f'/api/ai/restaurants/{self.rid}/reference').status_code, 404)

    def start(self, message='Generate menu.', request_id='request-1234567890'):
        with patch('menu_ai.threading.Thread'):
            response = self.call(self.url, 'POST', json={'message': message, 'requestId': request_id, 'revision': self.data['revision']})
        self.assertEqual(response.status_code, 202, response.json)
        return response.json['turns'][-1]['id']

    def run_job(self, tid):
        with patch('menu_ai.time.sleep'):
            self.service.run(tid, self.user['id'])

    def test_cancel_queued_prevents_provider_request(self):
        self.save_key()
        tid = self.start()
        url = self.url + '/' + tid + '/cancel'
        self.assertEqual(self.call(url, 'POST').json['turns'][-1]['status'], 'cancelling')
        self.assertEqual(self.call(url, 'POST').status_code, 202)
        self.run_job(tid)
        self.assertEqual(FakeOpenAI.instances, [])
        self.assertEqual(self.call(self.url).json['turns'][-1]['status'], 'cancelled')

    def test_cancel_running_calls_openai_and_discards_result(self):
        self.save_key()
        tid = self.start()
        original = FakeOpenAI.call
        def call(client, method, path, **kwargs):
            result = original(client, method, path, **kwargs)
            if method == 'POST' and path == '/responses':
                self.service.cancel(self.user['id'], self.rid, tid)
            if path.endswith('/cancel'):
                return FakeResponse({'status': 'cancelled'})
            return result
        with patch.object(FakeOpenAI, 'call', call):
            self.run_job(tid)
        turn = self.call(self.url).json['turns'][-1]
        self.assertEqual(turn['status'], 'cancelled')
        self.assertIsNone(turn['pdf'])
        calls = FakeOpenAI.instances[-1].calls
        self.assertTrue(any(method == 'POST' and path == '/responses/resp-test/cancel' for method, path, _ in calls))
        self.assertFalse(any(method == 'GET' for method, _, _ in calls))
        self.assertNotIn('could not be confirmed', turn['answer'])

    def test_cancel_provider_failure_is_reported(self):
        self.save_key()
        tid = self.start()
        original = FakeOpenAI.call
        def call(client, method, path, **kwargs):
            if path.endswith('/cancel'):
                raise GenerationError('Provider unavailable')
            result = original(client, method, path, **kwargs)
            if method == 'POST' and path == '/responses':
                self.service.cancel(self.user['id'], self.rid, tid)
            return result
        with patch.object(FakeOpenAI, 'call', call):
            self.run_job(tid)
        self.assertIn('could not be confirmed', self.call(self.url).json['turns'][-1]['answer'])

    def test_cancel_is_owner_scoped_and_origin_protected(self):
        self.save_key()
        tid = self.start()
        url = self.url + '/' + tid + '/cancel'
        self.assertEqual(self.client.post(url, base_url='https://menu.test').status_code, 403)
        self.call('/login', 'POST', data={'username': 'editor', 'password': 'test-password'})
        self.assertEqual(self.call(url, 'POST').status_code, 404)
        self.run_job(tid)

    def test_cancel_completed_preserves_pdf(self):
        self.save_key()
        tid = self.start()
        self.run_job(tid)
        turn = self.call(self.url + '/' + tid + '/cancel', 'POST').json['turns'][-1]
        self.assertEqual(turn['status'], 'completed')
        self.assertIsNotNone(turn['pdf'])

    def test_cancel_during_pdf_validation_cannot_publish(self):
        self.save_key()
        tid = self.start()
        def validate(*args):
            self.service.cancel(self.user['id'], self.rid, tid)
            return 1, []
        with patch('menu_ai.validate_pdf', side_effect=validate):
            self.run_job(tid)
        turn = self.call(self.url).json['turns'][-1]
        self.assertEqual(turn['status'], 'cancelled')
        self.assertIsNone(turn['pdf'])

    def test_only_alain_can_manage_key_and_raw_key_never_returned(self):
        self.save_key()
        with self.service.db() as db:
            stored = db.execute('SELECT value FROM settings').fetchone()[0]
            self.assertNotIn(b'sk-test', stored)
        self.assertEqual(self.call('/api/ai/key').json, {'configured': True, 'canManage': True})
        self.call('/login', 'POST', data={'username': 'editor', 'password': 'test-password'})
        self.assertEqual(self.call('/api/ai/key', 'PUT', json={'key': 'bad'}).status_code, 403)
        self.assertEqual(self.call('/api/ai/key', 'DELETE').status_code, 403)
        self.assertEqual(self.call('/api/ai/key').json, {'configured': True, 'canManage': False})

    def test_auth_origin_and_missing_key_are_enforced(self):
        response = self.call(self.url, 'POST', json={'message': 'Generate', 'requestId': 'request-1234567890', 'revision': self.data['revision']})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Alain', response.json['error'])
        self.assertEqual(self.client.put('/api/ai/key', base_url='https://menu.test', json={'key':'sk-test-key-never-expose-123456789'}).status_code, 403)
        self.call('/logout', 'POST')
        self.assertEqual(self.call('/api/ai/key').status_code, 401)
        self.assertEqual(self.call(self.url).status_code, 401)

    def test_configured_account_controls_api_key_and_ui_capability(self):
        self.app=create_app(dict(self.config,AI_KEY_USERNAME='editor'));self.client=self.app.test_client()
        self.call('/login','POST',data={'username':'editor','password':'test-password'})
        self.assertTrue(self.call('/api/runtime').json['user']['canManageApiKey'])
        self.save_key()
        self.call('/login','POST',data={'username':'alain','password':'test-password'})
        self.assertFalse(self.call('/api/runtime').json['user']['canManageApiKey'])
        self.assertEqual(self.call('/api/ai/key','PUT',json={'key':'sk-replacement-1234567890123456'}).status_code,403)

    def test_generation_revision_and_input_validation(self):
        self.save_key()
        for body, code in [(None,400), ({'revision': -1},409), ({'revision': self.data['revision'], 'message': [], 'requestId': 'request-1234567890'},400)]:
            self.assertEqual(self.call(self.url, 'POST', json=body).status_code, code)
        self.assertEqual(self.call('/api/ai/restaurants/not-found/conversation').status_code, 404)

    def test_duplicate_requests_do_not_bill_twice_and_parallel_turn_is_rejected(self):
        self.save_key(); first = self.start(); second = self.start()
        self.assertEqual(first, second)
        response = self.call(self.url, 'POST', json={'revision': self.data['revision'], 'message': 'Again', 'requestId': 'different-request-1234'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.call(self.url).json['turns']), 1)

    def test_full_generation_pdf_preview_private_files_and_no_menu_mutations(self):
        self.save_key(); tid = self.start(); self.run_job(tid)
        turn = self.call(self.url).json['turns'][0]
        self.assertEqual(turn['status'], 'completed'); self.assertEqual(turn['pages'], 1)
        self.assertNotIn('sandbox:', turn['answer'])
        response = self.call(turn['pdf'])
        self.assertEqual(response.mimetype, 'application/pdf'); response.close()
        response = self.call(turn['previews'][0]); self.assertEqual(response.mimetype, 'image/png'); response.close()
        self.assertEqual(self.call('/api/menus').json, self.data)
        provider = FakeOpenAI.instances[0]
        payload = next(kw['json'] for method,path,kw in provider.calls if path == '/responses')
        self.assertEqual(payload['model'], MODEL); self.assertTrue(payload['background'])
        self.assertEqual(payload['tools'][0]['type'], 'code_interpreter')
        self.assertNotIn(provider.key, json.dumps(payload))
        self.call('/login', 'POST', data={'username':'editor','password':'test-password'})
        self.assertEqual(self.call(turn['pdf']).status_code,404)
        self.assertEqual(self.call(turn['previews'][0]).status_code,404)
        self.assertEqual(self.call(self.url).json['turns'],[])

    def test_adjustment_receives_history_previous_pdf_source_and_fresh_data(self):
        self.save_key(); first=self.start(); self.run_job(first)
        self.restaurant['designPrompt']='Latest design instructions'
        with patch('menu_ai.threading.Thread'):
            second=self.service.start(self.user,self.restaurant,self.data['revision']+1,'Increase category spacing.','request-follow-up-1234')
        self.run_job(second)
        with zipfile.ZipFile(io.BytesIO(FakeOpenAI.instances[-1].uploads[0])) as z:
            names=z.namelist()
            self.assertIn('previous.pdf',names);self.assertIn('previous-source.zip',names)
            self.assertIn('koi-menu-pdf/SKILL.md',names);self.assertIn('reference.pdf',names)
            self.assertIn('koi-menu-pdf/scripts/build_mahakam_menu.py',names)
            self.assertIn('Increase category spacing.',z.read('request.json').decode())
            self.assertEqual(json.loads(z.read('restaurant.json'))['designPrompt'],'Latest design instructions')
            self.assertEqual(len(json.loads(z.read('conversation.json'))),1)
            self.assertFalse(any('credentials' in name or '.deployment' in name for name in names))

    def test_provider_failure_preserves_previous_pdf_and_releases_slot(self):
        self.save_key();first=self.start();self.run_job(first)
        FakeOpenAI.fail=True;second=self.start('Adjust','request-adjust-1234');self.run_job(second)
        turns=self.call(self.url).json['turns']
        self.assertEqual(turns[-1]['status'],'failed');self.assertTrue(turns[0]['pdf'])
        self.assertTrue(self.service.slots.acquire(blocking=False));self.service.slots.release()

    def test_incomplete_usage_survives_cleanup_and_restart_without_private_output(self):
        self.save_key(); tid = self.start()
        original = FakeOpenAI.call
        def incomplete(client, method, path, **kwargs):
            if method == 'GET' and path == '/responses/resp-test':
                return FakeResponse({'id': 'resp-test', 'status': 'incomplete',
                    'incomplete_details': {'reason': 'max_output_tokens'},
                    'error': {'code': 'server_error', 'message': 'private provider message'},
                    'instructions': 'private prompt',
                    'usage': {'input_tokens': 1200, 'output_tokens': 24000, 'total_tokens': 25200,
                              'output_tokens_details': {'reasoning_tokens': 20000}},
                    'output': [{'type': 'code_interpreter_call', 'container_id': 'cntr-test',
                                'status': 'completed', 'code': 'private generated code'}]})
            return original(client, method, path, **kwargs)
        with patch.object(FakeOpenAI, 'call', incomplete): self.run_job(tid)
        turn = self.call(self.url).json['turns'][-1]
        self.assertEqual(turn['status'], 'failed')
        self.assertIn('output-token limit', turn['error'])
        details = turn['diagnostics']
        self.assertEqual(details['incompleteReason'], 'max_output_tokens')
        self.assertEqual(details['usage']['output_tokens'], 24000)
        self.assertEqual(details['usage']['reasoning_tokens'], 20000)
        self.assertIsNone(details['usage']['cached_tokens'])
        self.assertEqual(details['codeStepsCompleted'], 1)
        self.assertNotIn('private', json.dumps(details))
        self.assertTrue(any(method == 'DELETE' and path == '/responses/resp-test'
                            for method, path, _ in FakeOpenAI.instances[-1].calls))
        restarted = create_app(self.config).extensions['menu_ai']
        self.assertEqual(restarted.chat(self.user['id'], self.rid)['turns'][-1]['diagnostics'], details)
        self.call('/login', 'POST', data={'username': 'editor', 'password': 'test-password'})
        self.assertEqual(self.call(self.url).json['turns'], [])

    def test_http_failure_metadata_is_retained(self):
        self.save_key(); tid = self.start()
        with patch.object(FakeOpenAI, 'call', side_effect=GenerationError('Rate limited.',
                          {'failureKind': 'http_error', 'httpStatus': 429, 'errorCode': 'rate_limit_exceeded'})):
            self.run_job(tid)
        details = self.call(self.url).json['turns'][-1]['diagnostics']
        self.assertEqual(details['httpStatus'], 429)
        self.assertEqual(details['errorCode'], 'rate_limit_exceeded')
        self.assertNotIn('usage', details)

    def test_fresh_generation_uses_current_data_without_previous_artifacts(self):
        self.save_key(); first = self.start(); self.run_job(first)
        with patch('menu_ai.threading.Thread'):
            response = self.call(self.url, 'POST', json={'message': 'Recreate from current saved data.',
                'requestId': 'fresh-menu-request-1234', 'mode': 'fresh', 'revision': -1})
        self.assertEqual(response.status_code, 202)
        tid = response.json['turns'][-1]['id']
        raw, snapshot = self.service.bundle(tid)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertNotIn('previous.pdf', archive.namelist())
            self.assertNotIn('previous-source.zip', archive.namelist())
            self.assertEqual(json.loads(archive.read('conversation.json')), [])
            request = json.loads(archive.read('request.json'))
            self.assertEqual(request['mode'], 'fresh')
            self.assertEqual(request['savedRevision'], self.data['revision'])
            self.assertEqual(json.loads(archive.read('restaurant.json')), snapshot)
        self.run_job(tid)
        self.assertEqual(len(self.call(self.url).json['turns']), 2)
        adjustment = self.start('Adjust spacing.', 'adjust-after-fresh-1234')
        raw, _ = self.service.bundle(adjustment)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            history = json.loads(archive.read('conversation.json'))
            self.assertEqual([turn['id'] for turn in history], [tid])
            self.assertIn('previous.pdf', archive.namelist())

    def test_rooftop_generation_and_adjustment_use_only_rooftop_skill(self):
        self.save_key()
        snapshot = dict(self.restaurant, id=ROOFTOP_ID, name='Koi Rooftop')
        for index, message in enumerate(['Generate menu.', 'Increase spacing.']):
            with patch('menu_ai.threading.Thread'):
                tid = self.service.start(self.user, snapshot, self.data['revision'], message, f'rooftop-request-{index:010d}')
            self.run_job(tid)
            provider = FakeOpenAI.instances[-1]
            payload = next(kw['json'] for method, path, kw in provider.calls if path == '/responses')
            self.assertEqual(payload['instructions'], ROOFTOP_INSTRUCTIONS)
            with zipfile.ZipFile(io.BytesIO(provider.uploads[0])) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertIn('koi-rooftop-menu-pdf/SKILL.md', names)
                self.assertIn('koi-rooftop-menu-pdf/assets/rooftop-reference-page-2.png', names)
                self.assertFalse(any(name.startswith('koi-menu-pdf/') for name in names))
                self.assertEqual(archive.read('reference.pdf'), (self.service.root / 'ai-skills/koi-rooftop-menu-pdf/assets/rooftop-original.pdf').read_bytes())
                self.assertEqual(archive.read('koi-rooftop-menu-pdf/assets/menu-icons.js'), (self.service.root / 'dist/menu-icons.js').read_bytes())
                self.assertEqual(json.loads(archive.read('restaurant.json')), snapshot)
                if index:
                    self.assertIn('previous.pdf', names)
                    self.assertIn('previous-source.zip', names)
        self.assertEqual(self.call('/api/menus').json, self.data)

    def test_other_restaurants_keep_general_skill_even_with_similar_name(self):
        self.assertEqual(menu_skill(dict(self.restaurant, name='Another Rooftop')), 'koi-menu-pdf')
        self.save_key(); tid = self.start(); self.run_job(tid)
        payload = next(kw['json'] for method, path, kw in FakeOpenAI.instances[-1].calls if path == '/responses')
        self.assertEqual(payload['instructions'], INSTRUCTIONS)

    def test_kuningan_drinks_bundle_isolated_from_lunch_and_rooftop(self):
        self.save_key()
        snapshot = dict(self.restaurant, id=KUNINGAN_DRINKS_ID,
                        name='KOI Kuningan Drinks and Cocktail',
                        source='Kuningan Fingerood Drinks Menu 20260720.pdf')
        for index, message in enumerate(['Generate menu.', 'Increase spacing.']):
            with patch('menu_ai.threading.Thread'):
                tid = self.service.start(self.user, snapshot, self.data['revision'], message,
                                         f'kuningan-drinks-{index:010d}')
            self.run_job(tid)
            provider = FakeOpenAI.instances[-1]
            payload = next(kw['json'] for method, path, kw in provider.calls if path == '/responses')
            self.assertEqual(payload['instructions'], KUNINGAN_DRINKS_INSTRUCTIONS)
            with zipfile.ZipFile(io.BytesIO(provider.uploads[0])) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertIn('koi-kuningan-drinks-menu-pdf/SKILL.md', names)
                self.assertIn('koi-kuningan-drinks-menu-pdf/assets/kuningan-drinks-reference.png', names)
                self.assertFalse(any(n.startswith(('koi-menu-pdf/', 'koi-rooftop-menu-pdf/')) for n in names))
                reference = self.service.root / 'ai-skills/koi-kuningan-drinks-menu-pdf/assets/kuningan-drinks-original.pdf'
                self.assertEqual(archive.read('reference.pdf'), reference.read_bytes())
                self.assertEqual(json.loads(archive.read('restaurant.json')), snapshot)
                if index:
                    self.assertIn('previous.pdf', names)
                    self.assertIn('previous-source.zip', names)
        self.assertEqual(menu_skill(dict(self.restaurant, name=snapshot['name'])), 'koi-menu-pdf')
        self.assertEqual(self.call('/api/menus').json, self.data)

    def test_mahakam_drinks_uses_own_skill_and_reference_for_generation_and_revision(self):
        self.save_key()
        snapshot = dict(self.restaurant, id=MAHAKAM_DRINKS_ID,
                        name='KOI Mahakam Drinks and Cocktail',
                        source='Mahakam Fingerfood Drinks Standart Menu November.pdf')
        for index, message in enumerate(['Generate menu.', 'Increase spacing.']):
            with patch('menu_ai.threading.Thread'):
                tid = self.service.start(self.user, snapshot, self.data['revision'], message,
                                         f'mahakam-drinks-{index:010d}')
            self.run_job(tid)
            provider = FakeOpenAI.instances[-1]
            payload = next(kw['json'] for method, path, kw in provider.calls if path == '/responses')
            self.assertEqual(payload['instructions'], MAHAKAM_DRINKS_INSTRUCTIONS)
            with zipfile.ZipFile(io.BytesIO(provider.uploads[0])) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertIn('koi-mahakam-drinks-menu-pdf/SKILL.md', names)
                self.assertIn('koi-mahakam-drinks-menu-pdf/assets/mahakam-drinks-reference.png', names)
                self.assertFalse(any(n.startswith(('koi-menu-pdf/', 'koi-rooftop-menu-pdf/',
                                                  'koi-kuningan-drinks-menu-pdf/')) for n in names))
                reference = self.service.root / 'ai-skills/koi-mahakam-drinks-menu-pdf/assets/mahakam-drinks-original.pdf'
                self.assertEqual(archive.read('reference.pdf'), reference.read_bytes())
                self.assertEqual(json.loads(archive.read('restaurant.json')), snapshot)
                if index:
                    self.assertIn('previous.pdf', names)
                    self.assertIn('previous-source.zip', names)
        self.assertEqual(menu_skill(dict(self.restaurant, name=snapshot['name'])), 'koi-menu-pdf')
        self.assertEqual(self.call('/api/menus').json, self.data)

    def test_rooftop_drinks_is_separate_from_rooftop_lunch_for_generation_and_revision(self):
        self.save_key()
        snapshot = dict(self.restaurant, id=ROOFTOP_DRINKS_ID,
                        name='KOI Rooftop Drinks and Cocktail',
                        source='KOI ROOFTOP Menu - Drinks & Cocktails November.pdf')
        for index, message in enumerate(['Generate menu.', 'Increase spacing.']):
            with patch('menu_ai.threading.Thread'):
                tid = self.service.start(self.user, snapshot, self.data['revision'], message,
                                         f'rooftop-drinks-{index:010d}')
            self.run_job(tid)
            provider = FakeOpenAI.instances[-1]
            payload = next(kw['json'] for method, path, kw in provider.calls if path == '/responses')
            self.assertEqual(payload['instructions'], ROOFTOP_DRINKS_INSTRUCTIONS)
            with zipfile.ZipFile(io.BytesIO(provider.uploads[0])) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertIn('koi-rooftop-drinks-menu-pdf/SKILL.md', names)
                for page in (1, 2):
                    self.assertIn(f'koi-rooftop-drinks-menu-pdf/assets/rooftop-drinks-reference-page-{page}.png', names)
                self.assertFalse(any(n.startswith(('koi-menu-pdf/', 'koi-rooftop-menu-pdf/',
                                                  'koi-kuningan-drinks-menu-pdf/',
                                                  'koi-mahakam-drinks-menu-pdf/')) for n in names))
                reference = self.service.root / 'ai-skills/koi-rooftop-drinks-menu-pdf/assets/rooftop-drinks-original.pdf'
                self.assertEqual(archive.read('reference.pdf'), reference.read_bytes())
                self.assertEqual(json.loads(archive.read('restaurant.json')), snapshot)
                if index:
                    self.assertIn('previous.pdf', names)
                    self.assertIn('previous-source.zip', names)
        self.assertEqual(menu_skill(dict(snapshot, id=ROOFTOP_ID)), 'koi-rooftop-menu-pdf')
        self.assertEqual(menu_skill(dict(self.restaurant, name=snapshot['name'])), 'koi-menu-pdf')
        self.assertEqual(self.call('/api/menus').json, self.data)

    def test_no_pdf_is_reported_as_clarification_not_false_success(self):
        self.save_key();FakeOpenAI.no_pdf=True;tid=self.start();self.run_job(tid)
        turn=self.call(self.url).json['turns'][0]
        self.assertIsNone(turn['pdf']);self.assertIn('No new PDF',turn['warnings'][0])

    def test_restart_keeps_key_and_history_but_marks_interrupted_job(self):
        self.save_key();self.start()
        restarted=create_app(self.config).extensions['menu_ai']
        self.assertEqual(restarted.key(),self.service.key())
        self.assertEqual(restarted.chat(self.user['id'],self.rid)['turns'][0]['status'],'failed')

    def test_key_removal_and_changed_encryption_secret_fail_closed(self):
        self.save_key()
        restarted=create_app(dict(self.config,SECRET_KEY='changed-secret')).extensions['menu_ai']
        self.assertFalse(restarted.key_status(self.user)['configured'])
        self.assertFalse(self.call('/api/ai/key','DELETE').json['configured'])

    def test_pdf_validator_rejects_invalid_and_warns_on_missing_dishes(self):
        with self.assertRaises(GenerationError):validate_pdf(b'not a PDF',self.restaurant,Path(self.temp.name))
        pages,warnings=validate_pdf(sample_pdf(),self.restaurant,Path(self.temp.name))
        self.assertEqual(pages,1);self.assertTrue(any('not found' in w for w in warnings))

    def test_provider_errors_do_not_expose_key_or_response_body(self):
        client=OpenAI('sk-private')
        response=requests.Response();response.status_code=401;response._content=b'{"error":"sk-private"}';response._content_consumed=True
        with patch.object(client.session,'request',return_value=response):
            with self.assertRaises(GenerationError) as caught:client.call('GET','/models')
        self.assertNotIn('sk-private',str(caught.exception));client.close()


if __name__=='__main__':unittest.main()
