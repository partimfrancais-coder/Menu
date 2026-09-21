"""Authenticated Railway entrypoint. Keep a single process for file-level locking."""
from datetime import timedelta
from pathlib import Path
import json
import os
import shutil
import threading
import time

from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from server import validate, restaurant_export, replace_restaurant, write_replacement, ROOT, LIMIT
from accounts import Accounts
from public_menu import public_menu, public_image
from products import migrate, migrate_categories, migrate_cuisines, prepare_save


def create_app(config=None):
    app = Flask(__name__, static_folder=None, template_folder=str(ROOT/'templates'))
    app.config.update(
        SECRET_KEY=os.environ.get('MENU_SESSION_SECRET'),
        PASSWORD_HASH=os.environ.get('MENU_PASSWORD_HASH'),
        USERNAME=os.environ.get('MENU_USERNAME', 'admin'),
        ADDITIONAL_USERS_JSON=os.environ.get('MENU_ADDITIONAL_USERS', '{}'),
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
    try:
        additional_users=app.config['ADDITIONAL_USERS_JSON']
        if isinstance(additional_users,str): additional_users=json.loads(additional_users)
        if not isinstance(additional_users,dict): raise ValueError
        if any(not isinstance(username,str) or not username or len(username)>100 or not isinstance(password_hash,str) or not password_hash for username,password_hash in additional_users.items()):
            raise ValueError
        if app.config['USERNAME'] in additional_users: raise ValueError
    except (TypeError,ValueError,json.JSONDecodeError):
        raise RuntimeError('MENU_ADDITIONAL_USERS must be a JSON object mapping usernames to Werkzeug password hashes.') from None
    if not app.config['PUBLIC_ORIGIN'].startswith('https://'):
        raise RuntimeError('A trusted HTTPS MENU_PUBLIC_ORIGIN or Railway public domain is required.')
    app.wsgi_app=ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    directory=Path(app.config['DATA_DIR']); directory.mkdir(parents=True, exist_ok=True)
    data_path=directory/'menus.json'
    if not data_path.exists():
        # Exclusive create never replaces an existing volume on a later deployment.
        with data_path.open('x',encoding='utf-8') as dest:
            dest.write((ROOT/'data'/'menus.json').read_text(encoding='utf-8'))
    original=json.loads(data_path.read_text(encoding='utf-8'))
    if 'products' not in original or 'productCategories' not in original or any('cuisine' not in p for p in original.get('products',[])):
        updated=migrate_cuisines(migrate_categories(migrate(original))); validate(updated); updated['revision']=original['revision']+1
        shutil.copy2(data_path,data_path.with_suffix('.before-cuisine.json'))
        write_replacement(data_path,updated)
    else: validate(original)
    accounts=Accounts(directory/'accounts.sqlite3',app.config['USERNAME'],app.config['PASSWORD_HASH'],additional_users)
    app.extensions['accounts']=accounts
    lock=threading.Lock()
    attempts={}
    attempt_lock=threading.Lock()

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        # no-referrer makes browser form POSTs send Origin: null, breaking login.
        # Invitation tokens live in fragments, which are never sent as referrers.
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
        if request.path in ('/login','/invite','/invite.js','/styles.css'): return None
        if request.method in ('GET','HEAD') and request.endpoint in ('customer_page','customer_data','customer_asset','customer_image'): return None
        user=accounts.user(session.get('user_id',''))
        if not user or not user['active'] or session.get('user_version')!=user['version']:
            session.clear()
            if request.path.startswith('/api/'): return jsonify(error='Your session has expired. Sign in again; export a backup first if you have unsaved edits.'),401
            return redirect('/login')
        g.user=user
        if request.path.startswith('/users') and user['role']!='admin':
            return jsonify(error='Administrator access is required.'),403

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
        user=accounts.authenticate(username,password,app.config['PASSWORD_HASH']) if len(password)<=1024 and len(username)<=254 else None
        if not user:
            return render_template('login.html',error='Incorrect username or password.'),401
        with attempt_lock: attempts.pop(key,None)
        session.clear(); session['user_id']=user['id'];session['user_version']=user['version']; session.permanent=True
        return redirect('/')

    @app.route('/invite',methods=['GET','POST'])
    def accept_invite():
        error=''
        if request.method=='POST':
            key='invite:'+str(request.remote_addr);now=time.monotonic()
            with attempt_lock:
                recent=[t for t in attempts.get(key,[]) if now-t<900]
                if len(recent)>=10:return render_template('invite.html',error='Too many attempts. Try again in 15 minutes.'),429
                attempts[key]=recent+[now]
            try:
                user=accounts.accept(request.form.get('token',''),request.form.get('password',''))
                session.clear();session['user_id']=user['id'];session['user_version']=user['version'];session.permanent=True
                return redirect('/')
            except ValueError as exc:error=str(exc)
        return render_template('invite.html',error=error),400 if error else 200

    @app.route('/users',methods=['GET','POST'])
    def users():
        error='';link='';message=''
        if request.method=='POST':
            try:
                action=request.form.get('action')
                if action=='invite':
                    token=accounts.invite(request.form.get('email',''),request.form.get('role',''),g.user['id'])
                    link=app.config['PUBLIC_ORIGIN'].rstrip('/')+'/invite#'+token
                    message='Invitation created. Copy and share the link privately; no email has been sent.'
                elif action=='update':
                    accounts.manage(request.form.get('id',''),request.form.get('role',''),request.form.get('active')=='1',g.user['id'])
                    return redirect('/users')
                elif action=='revoke':
                    accounts.revoke(request.form.get('id',''),g.user['id']);return redirect('/users')
                else:raise ValueError('Invalid action.')
            except ValueError as exc:error=str(exc)
        people,invites=accounts.listing()
        return render_template('users.html',users=people,invites=invites,error=error,link=link,message=message),400 if error else 200

    @app.post('/logout')
    def logout():
        session.clear(); return redirect('/login')

    @app.get('/')
    def index(): return send_from_directory(ROOT/'dist','index.html')

    @app.get('/<name>')
    def asset(name):
        if name not in ('app.js','catalog.js','menu-icons.js','design-prompts.js','styles.css','index.html','invite.js'): return jsonify(error='Not found.'),404
        return send_from_directory(ROOT/'dist',name)

    @app.get('/sources/<name>')
    def source(name):
        if name not in ('Kemang Lunch & Dinner 20260605A.pdf','Kuningan Lunch & Dinner 20260606A.pdf','MAHAKAM LUNCH DINNER 20260605A.pdf'): return jsonify(error='Source not found.'),404
        return send_from_directory(ROOT,name)

    @app.get('/menu/<rid>')
    def customer_page(rid):
        with lock: current=json.loads(data_path.read_text(encoding='utf-8'))
        if not any(r['id']==rid for r in current['restaurants']): return 'Menu not found.',404
        return send_from_directory(ROOT/'dist','customer.html')

    @app.get('/api/public/menus/<rid>')
    def customer_data(rid):
        try:
            with lock: current=json.loads(data_path.read_text(encoding='utf-8'))
            return jsonify(public_menu(current,rid))
        except ValueError: return jsonify(error='Menu not found.'),404

    @app.get('/api/public/menus/<rid>/images/<iid>')
    def customer_image(rid,iid):
        try:
            with lock: current=json.loads(data_path.read_text(encoding='utf-8'))
            raw,mime=public_image(current,rid,iid)
            return app.response_class(raw,mimetype=mime)
        except ValueError:return 'Image not found.',404

    @app.get('/customer/<name>')
    def customer_asset(name):
        assets={'menu.css':'customer.css','menu.js':'customer.js','menu-icons.js':'menu-icons.js'}
        if name not in assets: return 'Not found.',404
        return send_from_directory(ROOT/'dist',assets[name])

    @app.get('/api/runtime')
    def runtime(): return jsonify(hosted=True,user={'username':g.user['username'],'role':g.user['role']})

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
                prepare_save(data,current); validate(data)
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

    @app.route('/api/restaurants/<rid>/data',methods=['GET','POST'])
    def restaurant_data(rid):
        try:
            with lock:
                current=json.loads(data_path.read_text(encoding='utf-8'))
                if request.method=='GET':return jsonify(restaurant_export(current,rid))
                body=request.get_json()
                if not isinstance(body,dict) or body.get('revision')!=current['revision']:
                    return jsonify(error='Menu changed. Reload before replacing data.'),409
                updated=replace_restaurant(current,rid,body.get('upload'))
                write_replacement(data_path,updated)
            return jsonify(updated)
        except (ValueError,TypeError,KeyError) as exc:return jsonify(error=str(exc)),400
        except OSError:return jsonify(error='Could not replace the restaurant data. Reload to check the saved state before retrying.'),500

    @app.errorhandler(HTTPException)
    def http_error(error): return jsonify(error=error.description),error.code
    return app
