"""Persistent accounts and single-use invitations; no raw invite tokens on disk."""
import hashlib
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash


class Accounts:
    def __init__(self, path, username, password_hash, additional_users=None):
        self.path = str(path)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1,
                    owner INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS invites (
                    id TEXT PRIMARY KEY, email TEXT NOT NULL, role TEXT NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL, expires INTEGER NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0);
            ''')
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                db.execute('INSERT INTO users VALUES (?,?,?,?,1,1,1)',
                           (secrets.token_hex(16), username.strip().casefold(), password_hash, 'admin'))
            for name, hashed_password in (additional_users or {}).items():
                db.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,1,1,0)',
                           (secrets.token_hex(16), name.strip().casefold(), hashed_password, 'editor'))

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn: yield conn
        finally: conn.close()

    def user(self, uid):
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            return dict(row) if row else None

    def authenticate(self, username, password, dummy_hash):
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username.strip().casefold(),)).fetchone()
        valid = check_password_hash(row['password_hash'] if row else dummy_hash, password)
        return dict(row) if row and row['active'] and valid else None

    def listing(self):
        with self.db() as db:
            users = [dict(r) for r in db.execute('SELECT id,username,role,active,owner FROM users ORDER BY owner DESC,username')]
            invites = [dict(r) for r in db.execute('SELECT id,email,role,expires FROM invites WHERE used=0 AND expires>? ORDER BY expires DESC', (int(time.time()),))]
        return users, invites

    def invite(self, email, role, actor_id):
        email = email.strip().casefold()
        if len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Enter a valid email address.')
        if role not in ('admin', 'editor'): raise ValueError('Choose Admin or Editor.')
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.require_admin(db, actor_id)
            if db.execute('SELECT 1 FROM users WHERE username=?', (email,)).fetchone():
                raise ValueError('This account already exists. Manage its access below.')
            db.execute('UPDATE invites SET used=1 WHERE email=?', (email,))
            db.execute('INSERT INTO invites VALUES (?,?,?,?,?,0)', (secrets.token_hex(16),email,role,hashlib.sha256(token.encode()).hexdigest(),int(time.time())+7*86400))
        return token

    @staticmethod
    def require_admin(db, uid):
        actor=db.execute('SELECT role,active FROM users WHERE id=?',(uid,)).fetchone()
        if not actor or not actor['active'] or actor['role']!='admin':
            raise ValueError('Administrator access is required.')

    def accept(self, token, password):
        if not isinstance(token,str) or len(token)>128: raise ValueError('Invalid or expired invitation.')
        if not 12<=len(password)<=128: raise ValueError('Use a password between 12 and 128 characters.')
        hashed = generate_password_hash(password)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM invites WHERE token_hash=? AND used=0 AND expires>?',
                           (hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
            if not row: raise ValueError('Invalid or expired invitation. Ask an admin for a new link.')
            if db.execute('SELECT 1 FROM users WHERE username=?',(row['email'],)).fetchone():
                raise ValueError('This account already exists. Sign in instead.')
            uid=secrets.token_hex(16)
            db.execute('INSERT INTO users VALUES (?,?,?,?,1,1,0)',(uid,row['email'],hashed,row['role']))
            db.execute('UPDATE invites SET used=1 WHERE id=?',(row['id'],))
        return self.user(uid)

    def manage(self, uid, role, active, actor_id):
        if role not in ('admin','editor'): raise ValueError('Invalid role.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.require_admin(db,actor_id)
            target=db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            if not target: raise ValueError('User not found.')
            if target['owner'] and (role!='admin' or not active):
                raise ValueError('The owner account must remain an active administrator.')
            if uid==actor_id and (role!='admin' or not active):
                raise ValueError('You cannot remove your own administrator access.')
            db.execute('UPDATE users SET role=?,active=?,version=version+1 WHERE id=?',(role,int(active),uid))

    def revoke(self, invite_id, actor_id):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.require_admin(db,actor_id)
            db.execute('UPDATE invites SET used=1 WHERE id=?',(invite_id,))
