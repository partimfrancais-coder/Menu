"""Immutable restaurant design versions stored on the persistent menu volume."""
import os
from pathlib import Path
import re
import shutil
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager


class DesignVersions:
    def __init__(self, directory, root, skill_for, reference_for):
        self.directory = Path(directory) / 'design-versions'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.root = Path(root)
        self.skill_for = skill_for
        self.reference_for = reference_for
        self.lock = threading.RLock()
        self.database = self.directory / 'versions.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS versions (
                    restaurant TEXT NOT NULL, number INTEGER NOT NULL,
                    skill_name TEXT NOT NULL, created REAL NOT NULL,
                    parent INTEGER, prompt TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (restaurant, number));
                CREATE TABLE IF NOT EXISTS active (
                    restaurant TEXT PRIMARY KEY, number INTEGER NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db: yield db
        finally: db.close()

    @staticmethod
    def valid_restaurant(rid):
        if not re.fullmatch(r'(?:[0-9a-fA-F]{32}|[0-9a-fA-F-]{36})', rid):
            raise ValueError('Invalid restaurant ID.')

    def folder(self, rid, number):
        self.valid_restaurant(rid)
        if not isinstance(number, int) or number < 1 or number > 10000:
            raise ValueError('Invalid design version.')
        return self.directory / rid / f'v{number}'

    def ensure(self, snapshot):
        rid = snapshot['id']
        self.valid_restaurant(rid)
        with self.lock, self.connect() as db:
            if db.execute('SELECT 1 FROM versions WHERE restaurant=? AND number=1', (rid,)).fetchone():
                return
            skill_name = self.skill_for(snapshot)
            source = self.root / 'ai-skills' / skill_name
            reference = self.reference_for(self.root, snapshot)
            if not (source / 'SKILL.md').is_file() or reference is None or not reference.is_file():
                raise ValueError('This restaurant needs a skill and reference PDF before versioning.')
            destination = self.folder(rid, 1)
            if destination.exists():
                if not (destination / skill_name / 'SKILL.md').is_file() or not (destination / 'reference.pdf').is_file():
                    raise ValueError('The initial design copy is incomplete. Please contact the administrator.')
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)', (rid, 1, skill_name, time.time(), None, ''))
                db.execute('INSERT OR IGNORE INTO active VALUES (?,1)', (rid,))
                return
            temporary = destination.parent / f'.v1-{uuid.uuid4().hex}'
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                temporary.mkdir()
                shutil.copytree(source, temporary / skill_name)
                shutil.copy2(reference, temporary / 'reference.pdf')
                os.replace(temporary, destination)
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)', (rid, 1, skill_name, time.time(), None, ''))
                db.execute('INSERT INTO active VALUES (?,1)', (rid,))
            finally:
                if temporary.exists(): shutil.rmtree(temporary)

    def listing(self, snapshot):
        self.ensure(snapshot)
        rid = snapshot['id']
        with self.connect() as db:
            rows = db.execute('SELECT number,skill_name,created,parent,prompt FROM versions WHERE restaurant=? ORDER BY number', (rid,)).fetchall()
            active = db.execute('SELECT number FROM active WHERE restaurant=?', (rid,)).fetchone()['number']
        versions=[]
        for row in rows:
            version=dict(row)
            version['label']=f"v{row['number']}"
            version['active']=row['number']==active
            versions.append(version)
        return {'activeVersion':active,'versions':versions}

    def resolve(self, snapshot, number=None):
        self.ensure(snapshot)
        rid=snapshot['id']
        with self.connect() as db:
            if number is None:
                number=db.execute('SELECT number FROM active WHERE restaurant=?', (rid,)).fetchone()['number']
            row=db.execute('SELECT skill_name FROM versions WHERE restaurant=? AND number=?', (rid,number)).fetchone()
        if row is None: raise ValueError('Design version not found.')
        folder=self.folder(rid,number)
        skill=folder/row['skill_name']
        reference=folder/'reference.pdf'
        if not (skill/'SKILL.md').is_file() or not reference.is_file():
            raise ValueError('This design version is missing its skill or reference PDF.')
        return {'number':number,'skillName':row['skill_name'],'skill':skill,'reference':reference}

    def activate(self, snapshot, number):
        selected=self.resolve(snapshot,number)
        with self.lock, self.connect() as db:
            db.execute('UPDATE active SET number=? WHERE restaurant=?',(number,snapshot['id']))
        return selected

    def create(self, snapshot, parent, skill_markdown, reference_pdf, prompt=''):
        self.validate_pair(skill_markdown,reference_pdf)
        source=self.resolve(snapshot,parent)
        rid=snapshot['id']
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            number=db.execute('SELECT MAX(number) FROM versions WHERE restaurant=?',(rid,)).fetchone()[0]+1
            destination=self.folder(rid,number)
            temporary=destination.parent/f'.v{number}-{uuid.uuid4().hex}'
            try:
                shutil.copytree(self.folder(rid,parent),temporary)
                (temporary/source['skillName']/'SKILL.md').write_bytes(skill_markdown.encode('utf-8'))
                (temporary/'reference.pdf').write_bytes(reference_pdf)
                for asset in (temporary/source['skillName']/'assets').glob('*original.pdf'):
                    asset.write_bytes(reference_pdf)
                os.replace(temporary,destination)
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)',(rid,number,source['skillName'],time.time(),parent,prompt[:6000]))
            finally:
                if temporary.exists():shutil.rmtree(temporary)
        return number

    @staticmethod
    def validate_pair(skill_markdown,reference_pdf):
        if not isinstance(skill_markdown,str) or not 20<=len(skill_markdown)<=200000:
            raise ValueError('The new skill must contain 20–200,000 characters.')
        if not isinstance(reference_pdf,bytes) or not reference_pdf.startswith(b'%PDF-') or len(reference_pdf)>25*1024*1024:
            raise ValueError('The new reference must be a PDF under 25 MB.')
        import fitz
        try:
            with fitz.open(stream=reference_pdf,filetype='pdf') as pdf:
                if pdf.is_encrypted or not 1<=len(pdf)<=30: raise ValueError
        except Exception:
            raise ValueError('The reference PDF could not be opened or is encrypted.') from None

    def initialize_from_files(self,snapshot,skill_markdown,reference_pdf):
        self.validate_pair(skill_markdown,reference_pdf)
        rid=snapshot['id']
        skill_name=self.skill_for(snapshot)
        source=self.root/'ai-skills'/skill_name
        if not (source/'SKILL.md').is_file():raise ValueError('The base skill is unavailable.')
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM versions WHERE restaurant=?',(rid,)).fetchone():
                raise ValueError('This restaurant already has v1.')
            destination=self.folder(rid,1)
            temporary=destination.parent/f'.v1-{uuid.uuid4().hex}'
            destination.parent.mkdir(parents=True,exist_ok=True)
            try:
                temporary.mkdir()
                shutil.copytree(source,temporary/skill_name)
                (temporary/skill_name/'SKILL.md').write_bytes(skill_markdown.encode('utf-8'))
                (temporary/'reference.pdf').write_bytes(reference_pdf)
                for asset in (temporary/skill_name/'assets').glob('*original.pdf'):
                    asset.write_bytes(reference_pdf)
                os.replace(temporary,destination)
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?)',(rid,1,skill_name,time.time(),None,'Uploaded initial version'))
                db.execute('INSERT INTO active VALUES (?,1)',(rid,))
            finally:
                if temporary.exists():shutil.rmtree(temporary)
        return 1
