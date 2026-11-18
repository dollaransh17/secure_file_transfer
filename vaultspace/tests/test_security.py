"""Integration checks against a disposable database and real HTTP server."""
import base64
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory()
os.environ['VAULT_DATA_DIR'] = TEMP.name
import secrets
os.environ['VAULT_DEMO_PASSWORD'] = secrets.token_urlsafe(24)
import server

class SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.initialize()
        cls.http = server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.url = 'http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread = threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        TEMP.cleanup()

    def request(self,client,path,body=None,csrf=None,headers=None):
        h = {'Content-Type':'application/json',**(headers or {})}
        if csrf is not None: h['X-CSRF-Token']=csrf
        req=Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        try:
            with client.open(req) as r:
                data=r.read()
                return r.status,json.loads(data) if r.headers['Content-Type']=='application/json' else data,r.headers
        except HTTPError as e:
            return e.code,json.loads(e.read()),e.headers

    def login(self,who='a'):
        client=build_opener(HTTPCookieProcessor(CookieJar()))
        email='alex@vaultspace.demo' if who=='a' else 'jamie@vaultspace.demo'
        status,result,headers=self.request(client,'/api/login',{'email':email,'password':server.DEMO_PASSWORD})
        self.assertEqual(status,200)
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        return client,result['csrf']

    def test_authentication_csrf_and_logout(self):
        anon=build_opener()
        self.assertEqual(self.request(anon,'/api/workspace')[0],401)
        self.assertEqual(self.request(anon,'/api/login',{'email':'alex@vaultspace.demo','password':'wrong'})[0],401)
        a,csrf=self.login()
        self.assertEqual(self.request(a,'/api/upload',{'name':'test.txt','content':'eA=='})[0],403)
        self.assertEqual(self.request(a,'/api/logout',{},csrf,{'Origin':'http://evil.example'})[0],403)
        self.assertEqual(self.request(a,'/api/logout',{},csrf)[0],200)
        self.assertEqual(self.request(a,'/api/workspace')[0],401)

    def test_user_isolation_and_upload_validation(self):
        a,ca=self.login('a');b,cb=self.login('b')
        files=self.request(a,'/api/workspace')[1]['files'];fid=files[0]['id']
        self.assertTrue(all(f['owner']=='user-b' for f in self.request(b,'/api/workspace')[1]['files']))
        for path,body in [('/api/files/'+fid+'/download',None),('/api/delete',{'file_id':fid}),('/api/share',{'file_id':fid})]:
            self.assertEqual(self.request(b,path,body,cb)[0],404)
        self.assertEqual(self.request(a,'/api/files/'+fid+'/download')[0],200)
        self.assertEqual(self.request(a,'/api/upload',{'name':'payload.html','content':'eA=='},ca)[0],400)
        self.assertEqual(self.request(a,'/api/upload',{'name':'huge.txt','content':base64.b64encode(b'x'*(server.MAX_FILE+1)).decode()},ca)[0],400)
        self.assertEqual(self.request(a,'/api/upload',{'name':'Demo.txt','content':base64.b64encode(b'hello').decode()},ca)[0],201)
        uploaded=next(f for f in self.request(a,'/api/workspace')[1]['files'] if f['name']=='Demo.txt')
        self.assertEqual(self.request(a,'/api/files/'+uploaded['id']+'/download')[1],b'hello')
        self.assertEqual(self.request(a,'/api/delete',{'file_id':uploaded['id']},ca)[0],200)
        self.assertEqual(self.request(a,'/api/files/'+uploaded['id']+'/download')[0],404)
        self.assertTrue(any(e['action']=='access_denied' for e in self.request(b,'/api/workspace')[1]['events']))

    def test_share_expiry_revocation_and_delete(self):
        a,ca=self.login();b,cb=self.login('b');anon=build_opener()
        fid=self.request(a,'/api/workspace')[1]['files'][0]['id']
        def share():
            status,result,_=self.request(a,'/api/share',{'file_id':fid,'minutes':1},ca)
            self.assertEqual(status,200)
            return result['path'],hashlib.sha256(result['path'].split('/')[-1].encode()).hexdigest()
        path,sid=share()
        self.assertEqual(self.request(anon,path)[0],200)
        self.assertEqual(self.request(b,'/api/revoke',{'share_id':sid},cb)[0],404)
        self.assertEqual(self.request(a,'/api/revoke',{'share_id':sid},ca)[0],200)
        self.assertEqual(self.request(anon,path)[0],410)
        path,sid=share()
        with server.db() as c:c.execute('UPDATE shares SET expires=0 WHERE id=?',(sid,))
        self.assertEqual(self.request(anon,path)[0],410)
        path,sid=share()
        self.assertEqual(self.request(a,'/api/delete',{'file_id':fid},ca)[0],200)
        self.assertEqual(self.request(anon,path)[0],410)

    def test_registration_and_security_headers(self):
        c=build_opener(HTTPCookieProcessor(CookieJar()))
        self.assertEqual(self.request(c,'/api/register',{'name':'Test','email':'test@example.com','password':'short'})[0],400)
        status,result,_=self.request(c,'/api/register',{'name':'Test','email':'test@example.com','password':'A-long-password!2026'})
        self.assertEqual(status,200)
        self.assertEqual(self.request(c,'/api/workspace')[1]['files'],[])
        status,_,headers=self.request(c,'/')
        self.assertEqual(status,200)
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(self.request(c,'/storage.py')[0],404)

if __name__=='__main__': unittest.main(verbosity=2)
