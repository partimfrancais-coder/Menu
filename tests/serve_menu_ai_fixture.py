"""Local browser-test fixture: no real API calls or production data writes."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hosted import create_app
from test_menu_ai import FakeOpenAI
from werkzeug.security import generate_password_hash

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(dict(
            TESTING=True, SECRET_KEY='browser-fixture-only', USERNAME='alain',
            PASSWORD_HASH=generate_password_hash('browser-test-only'),
            DATA_DIR=directory, PUBLIC_ORIGIN='https://127.0.0.1:8779',
            AI_CLIENT_FACTORY=FakeOpenAI,
        ))
        app.run(host='127.0.0.1', port=8779, ssl_context='adhoc', use_reloader=False)
