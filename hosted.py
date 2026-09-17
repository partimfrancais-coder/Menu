"""Authenticated Railway entrypoint. Keep a single process for file-level locking."""
from datetime import timedelta
from pathlib import Path
import json
import os
import secrets
import shutil
import threading
import time

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash
from werkzeug.exceptions import HTTPException
from server import validate, ROOT, LIMIT


def create_app(config=None):
    app = Flask(__name__, static_folder=None, template_folder=str(ROOT/'templates'))
    app.config.update(
        SECRET_KEY=os.environ.get('MENU_SESSION_SECRET'),
        PASSWORD_HASH=os.environ.get('MENU_PASSWORD_HASH'),
        USERNAME=os.environ.get('MENU_USERNAME', 'admin'),
        DATA_DIR=os.environ.get('MENU_DATA_DIR', '/data'),
        PUBLIC_ORIGIN=os.environ.get('MENU_PUBLIC_ORIGIN') or ('https://'+os.environ['RAILWAY_PUBLIC_DOMAIN'] if os.environ.get('RAILWAY_PUBLIC_DOMAIN') else ''),
        MAX_CONTENT_LENGTH=LIMIT,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    if config: app.config.update(config)
    if not app.config['SECRET_KEY'] or not app.config['PASSWORD_HASH']:
        raise RuntimeError('MENU_SESSION_SECRET and MENU_PASSWORD_HASH must be configured.')
    if not app.config['PUBLIC_ORIGIN'].startswith('https://'):
        raise RuntimeError('A trusted HTTPS MENU_PUBLIC_ORIGIN or Railway public domain is required.')
    app.wsgi_app=ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    directory=Path(app.config['DATA_DIR']); directory.mkdir(parents=True, exist_ok=True)
    data_path=directory/'menus.json'
    if not data_path.exists():
        # Exclusive create never replaces an existing volume on a later deployment.
        with data_path.open('x',encoding='utf-8') as dest:
            dest.write((ROOT/'data'/'menus.json').read_text(encoding='utf-8'))
    validate(json.loads(data_path.read_text(encoding='utf-8')))
    lock=threading.Lock()
    attempts={}
    attempt_lock=threading.Lock()

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; object-src 'none'; form-action 'self'; base-uri 'self'"
        response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.before_request
    def protect():
        if request.path=='/health': return None
        expected=app.config['PUBLIC_ORIGIN'].rstrip('/')
        if request.host != expected.split('://',1)[1]:
            return jsonify(error='Invalid host.'),403
        if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('Origin')!=expected:
            return jsonify(error='Request origin was not accepted.'),403
        if request.path in ('/login','/styles.css'): return None
        if not session.get('authenticated'):
            if request.path.startswith('/api/'): return jsonify(error='Your session has expired. Sign in again; export a backup first if you have unsaved edits.'),401
            return redirect('/login')

    @app.get('/health')
    def health():
        try:
            with lock:
                current=json.loads(data_path.read_text(encoding='utf-8'))
                if not current.get('restaurants'): raise ValueError('No restaurants')
            return jsonify(status='ok')
        except (OSError,ValueError): return jsonify(status='unhealthy'),503

    @app.route('/login',methods=['GET','POST'])
    def login():
        if request.method=='GET': return render_template('login.html',error='')
        now=time.monotonic(); key=request.remote_addr or 'unknown'
        with attempt_lock:
            for ip in list(attempts):
                attempts[ip]=[stamp for stamp in attempts[ip] if now-stamp<900]
                if not attempts[ip]: attempts.pop(ip)
            recent=attempts.setdefault(key,[])
            if len(recent)>=10: return render_template('login.html',error='Too many attempts. Try again in 15 minutes.'),429
            recent.append(now)
        username=request.form.get('username',''); password=request.form.get('password','')
        if len(password)>1024 or not secrets.compare_digest(username.encode(),app.config['USERNAME'].encode()) or not check_password_hash(app.config['PASSWORD_HASH'],password):
            return render_template('login.html',error='Incorrect username or password.'),401
        with attempt_lock: attempts.pop(key,None)
        session.clear(); session['authenticated']=True; session.permanent=True
        return redirect('/')

    @app.post('/logout')
    def logout():
        session.clear(); return redirect('/login')

    @app.get('/')
    def index(): return send_from_directory(ROOT/'dist','index.html')

    @app.get('/<name>')
    def asset(name):
        if name not in ('app.js','catalog.js','menu-icons.js','design-prompts.js','styles.css','index.html'): return jsonify(error='Not found.'),404
        return send_from_directory(ROOT/'dist',name)

    @app.get('/sources/<name>')
    def source(name):
        if name not in ('Kemang Lunch & Dinner 20260605A.pdf','Kuningan Lunch & Dinner 20260606A.pdf'): return jsonify(error='Source not found.'),404
        return send_from_directory(ROOT,name)

    @app.get('/api/runtime')
    def runtime(): return jsonify(hosted=True)

    @app.route('/api/menus',methods=['GET','POST'])
    def menus():
        if request.method=='GET':
            with lock: current=json.loads(data_path.read_text(encoding='utf-8'))
            return jsonify(current)
        try:
            data=request.get_json(); validate(data)
            with lock:
                current=json.loads(data_path.read_text(encoding='utf-8'))
                if data.get('revision')!=current['revision']:
                    return jsonify(error='Another window changed the menu. Export your backup, then reload before continuing.'),409
                data['revision']=current['revision']+1
                temp=data_path.with_suffix('.tmp')
                with temp.open('w',encoding='utf-8') as target:
                    json.dump(data,target,ensure_ascii=False,indent=2); target.flush(); os.fsync(target.fileno())
                shutil.copy2(data_path,data_path.with_suffix('.previous.json'))
                os.replace(temp,data_path)
            return jsonify(revision=data['revision'])
        except (ValueError,TypeError,KeyError) as exc: return jsonify(error=str(exc)),400
        except OSError:
            app.logger.error('Menu storage write failed.')
            return jsonify(error='Could not save the menu. Export a backup and try again.'),500

    @app.errorhandler(HTTPException)
    def http_error(error): return jsonify(error=error.description),error.code
    return app
