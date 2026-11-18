"""Vaultspace local secure software engineering demonstration. No third-party dependencies."""
import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, quote
from storage import LocalStorage

ROOT = Path(__file__).parent
DATA = Path(os.environ.get('VAULT_DATA_DIR', ROOT / '.data'))
DATA.mkdir(parents=True, exist_ok=True)
STORE = LocalStorage(DATA / 'objects')
MAX_FILE = 10 * 1024 * 1024
ALLOWED = {'.pdf', '.txt', '.csv', '.png', '.jpg', '.jpeg', '.docx', '.xlsx', '.pptx', '.md'}
DEMO_PASSWORD = os.environ.get('VAULT_DEMO_PASSWORD')

@contextmanager
def db():
    conn = sqlite3.connect(DATA / 'vault.db', timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

def audit(conn, uid, action, detail, outcome='success'):
    conn.execute('INSERT INTO events(user_id,action,detail,outcome,created) VALUES(?,?,?,?,?)', (uid, action, detail, outcome, time.time()))

def initialize():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,salt TEXT,password TEXT);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),csrf TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,owner TEXT REFERENCES users(id),name TEXT,size INTEGER,created REAL);
        CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY,file_id TEXT REFERENCES files(id) ON DELETE CASCADE,owner TEXT REFERENCES users(id),expires REAL,revoked INTEGER DEFAULT 0,created REAL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,user_id TEXT,action TEXT,detail TEXT,outcome TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS attempts(email TEXT,created REAL);
        ''')
        if not DEMO_PASSWORD:
            return
        for uid, name, email in [('user-a','Alex Morgan','alex@vaultspace.demo'),('user-b','Jamie Chen','jamie@vaultspace.demo')]:
            if c.execute('SELECT id FROM users WHERE id=?', (uid,)).fetchone():
                continue
            salt = secrets.token_hex(16)
            c.execute('INSERT INTO users VALUES(?,?,?,?,?)', (uid,name,email,salt,password_hash(DEMO_PASSWORD,salt)))
            for filename, content in [('Project brief.md', f'# Secure Cloud Storage\n\nPrivate project workspace for {name}.\n'.encode()), ('Security checklist.txt', b'Threat modeling\nServer-side authorization\nPrivate object storage\nExpiring links\nAudit logging\n'), ('Research notes.csv', b'topic,status\nauthentication,implemented\nAWS integration,planned\n')]:
                fid = secrets.token_hex(16)
                STORE.put(fid, content)
                c.execute('INSERT INTO files VALUES(?,?,?,?,?)', (fid,uid,filename,len(content),time.time()))
            audit(c,uid,'workspace_created','Demo workspace initialized')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log request paths: shared download paths contain bearer tokens.
        pass

    def headers_out(self, status, content_type='application/json', extra=None):
        self.send_response(status)
        for k,v in {'Content-Type':content_type,'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'", **(extra or {})}.items():
            self.send_header(k,v)
        self.end_headers()

    def json(self, value, status=200, extra=None):
        self.headers_out(status, extra=extra)
        self.wfile.write(json.dumps(value).encode())

    def body(self):
        size = int(self.headers.get('Content-Length','0'))
        if size < 0 or size > 15 * 1024 * 1024:
            raise ValueError('Request too large. Maximum file size is 10 MB.')
        return json.loads(self.rfile.read(size) or b'{}')

    def session(self, c):
        cookie = SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: return None
        token = cookie.get('vault_session')
        if not token: return None
        return c.execute('SELECT s.*,u.name,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE token=? AND expires>?', (hashlib.sha256(token.value.encode()).hexdigest(),time.time())).fetchone()

    def do_GET(self):
        try: self.get()
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception: self.json({'error':'Unable to complete request.'},500)

    def get(self):
        path = urlparse(self.path).path
        if path in ['/', '/app.js', '/style.css']:
            file = ROOT / 'static' / ('index.html' if path=='/' else path[1:])
            self.headers_out(200,mimetypes.guess_type(file)[0] or 'text/plain')
            self.wfile.write(file.read_bytes())
            return
        if path.startswith('/s/'):
            token = path.split('/')[-1]
            with db() as c:
                row = c.execute('SELECT f.*,s.owner share_owner FROM shares s JOIN files f ON f.id=s.file_id WHERE s.id=? AND s.revoked=0 AND s.expires>?', (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
                if not row: return self.json({'error':'This share link has expired or been revoked.'},410)
                audit(c,row['owner'],'shared_download',row['name'])
            return self.download(row)
        with db() as c:
            s = self.session(c)
            if not s: return self.json({'error':'Please sign in.'},401)
            uid = s['user_id']
            if path=='/api/session':
                return self.json({'user':{'id':uid,'name':s['name'],'email':s['email']},'csrf':s['csrf']})
            if path=='/api/workspace':
                files = [dict(r) for r in c.execute('SELECT * FROM files WHERE owner=? ORDER BY created DESC',(uid,))]
                shares = [dict(r) for r in c.execute('SELECT s.id,s.file_id,s.expires,s.revoked,s.created,f.name FROM shares s JOIN files f ON f.id=s.file_id WHERE s.owner=? ORDER BY s.created DESC',(uid,))]
                events = [dict(r) for r in c.execute('SELECT action,detail,outcome,created FROM events WHERE user_id=? ORDER BY id DESC LIMIT 100',(uid,))]
                return self.json({'files':files,'shares':shares,'events':events})
            if path.startswith('/api/files/') and path.endswith('/download'):
                fid = path.split('/')[3]
                row = c.execute('SELECT * FROM files WHERE id=? AND owner=?',(fid,uid)).fetchone()
                if not row:
                    audit(c,uid,'access_denied','Blocked download of a file outside this workspace','blocked')
                    return self.json({'error':'File not found or access denied.'},404)
                audit(c,uid,'download',row['name'])
                return self.download(row)
        self.json({'error':'Not found.'},404)

    def download(self,row):
        content = STORE.get(row['id'])
        self.headers_out(200,'application/octet-stream',{'Content-Disposition':"attachment; filename*=UTF-8''"+quote(row['name']), 'Content-Length':str(len(content))})
        self.wfile.write(content)

    def do_POST(self):
        try: self.post()
        except (ValueError, TypeError, KeyError): self.json({'error':'Invalid request. Check your inputs and try again.'},400)
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception: self.json({'error':'Unable to complete request.'},500)

    def post(self):
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host',''):
            return self.json({'error':'Request origin denied.'},403)
        path = urlparse(self.path).path
        body = self.body()
        with db() as c:
            if path in ['/api/login','/api/register']:
                email = str(body.get('email','')).strip().lower()
                password = str(body.get('password',''))
                c.execute('DELETE FROM attempts WHERE created<?',(time.time()-300,))
                if c.execute('SELECT COUNT(*) FROM attempts WHERE email=?',(email,)).fetchone()[0]>=10:
                    return self.json({'error':'Too many attempts. Try again in five minutes.'},429)
                c.execute('INSERT INTO attempts VALUES(?,?)',(email,time.time()))
                if path=='/api/register':
                    name = str(body.get('name','')).strip()
                    if not 2<=len(name)<=80 or '@' not in email or len(email)>254 or not 12<=len(password)<=128:
                        return self.json({'error':'Use a name, valid email, and a password of 12–128 characters.'},400)
                    if c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():
                        return self.json({'error':'Unable to register this email. Try signing in.'},400)
                    salt = secrets.token_hex(16)
                    c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(secrets.token_hex(16),name,email,salt,password_hash(password,salt)))
                user = c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                candidate = password_hash(password,user['salt'] if user else '00'*16)
                if not user or not hmac.compare_digest(candidate,user['password']):
                    return self.json({'error':'Email or password is incorrect.'},401)
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],csrf,time.time()+28800))
                audit(c,user['id'],'sign_in','Signed in to workspace')
                return self.json({'user':{'id':user['id'],'name':user['name'],'email':email},'csrf':csrf},extra={'Set-Cookie':f'vault_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
            s = self.session(c)
            if not s: return self.json({'error':'Please sign in.'},401)
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):
                return self.json({'error':'Invalid security token. Refresh and try again.'},403)
            uid = s['user_id']
            if path=='/api/logout':
                c.execute('DELETE FROM sessions WHERE token=?',(s['token'],))
                return self.json({'ok':True},extra={'Set-Cookie':'vault_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
            if path=='/api/upload':
                name = str(body.get('name','')).replace('\\','/').split('/')[-1].strip()
                if not name or len(name)>180 or any(ord(ch)<32 for ch in name) or Path(name).suffix.lower() not in ALLOWED:
                    audit(c,uid,'upload_rejected','Unsupported filename or file type','blocked')
                    return self.json({'error':'Allowed: PDF, TXT, CSV, Markdown, PNG, JPG, DOCX, XLSX, PPTX.'},400)
                content = base64.b64decode(body['content'], validate=True)
                if not content or len(content)>MAX_FILE:
                    return self.json({'error':'Choose a nonempty file up to 10 MB.'},400)
                if c.execute('SELECT COALESCE(SUM(size),0) FROM files WHERE owner=?',(uid,)).fetchone()[0]+len(content)>100*1024*1024:
                    return self.json({'error':'Your 100 MB local workspace is full.'},400)
                fid = secrets.token_hex(16)
                STORE.put(fid,content)
                c.execute('INSERT INTO files VALUES(?,?,?,?,?)',(fid,uid,name,len(content),time.time()))
                audit(c,uid,'upload',name)
                return self.json({'ok':True},201)
            if path in ['/api/delete','/api/share']:
                row = c.execute('SELECT * FROM files WHERE id=? AND owner=?',(body['file_id'],uid)).fetchone()
                if not row:
                    audit(c,uid,'access_denied','Blocked operation on a file outside this workspace','blocked')
                    return self.json({'error':'File not found or access denied.'},404)
                if path=='/api/delete':
                    c.execute('DELETE FROM files WHERE id=?',(row['id'],))
                    STORE.delete(row['id'])
                    audit(c,uid,'delete',row['name'])
                    return self.json({'ok':True})
                minutes = int(body.get('minutes',60))
                if minutes not in [1,15,60,1440]: return self.json({'error':'Invalid expiry.'},400)
                token = secrets.token_urlsafe(32)
                expires = time.time()+minutes*60
                c.execute('INSERT INTO shares VALUES(?,?,?,?,0,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],uid,expires,time.time()))
                audit(c,uid,'share_created',row['name'])
                return self.json({'path':'/s/'+token,'expires':expires})
            if path=='/api/revoke':
                row = c.execute('SELECT * FROM shares WHERE id=? AND owner=?',(body['share_id'],uid)).fetchone()
                if not row: return self.json({'error':'Share not found.'},404)
                c.execute('UPDATE shares SET revoked=1 WHERE id=?',(body['share_id'],))
                audit(c,uid,'share_revoked','Shared link revoked')
                return self.json({'ok':True})
        return self.json({'error':'Not found.'},404)

if __name__=='__main__':
    initialize()
    port = int(os.environ.get('PORT','8000'))
    server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Vaultspace running at http://127.0.0.1:{port}',flush=True)
    server.serve_forever()
