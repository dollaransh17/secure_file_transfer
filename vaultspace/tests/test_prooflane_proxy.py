import http.client
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import prooflane_dashboard as proxy
from urllib.parse import urlsplit

class Upstream(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*_): pass
    def do_POST(self):
        type(self).seen.append((self.headers.get('Origin'),self.headers.get('X-CSRF-Token'),self.rfile.read(int(self.headers.get('Content-Length',0)))))
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Set-Cookie','prooflane_session=test; HttpOnly; SameSite=Strict; Path=/');self.end_headers();self.wfile.write(b'{"ok":true}')

class ProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.up=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        proxy.UPSTREAM=urlsplit('http://127.0.0.1:'+str(cls.up.server_port))
        cls.web=ThreadingHTTPServer(('127.0.0.1',0),proxy.Handler)
        for s in (cls.up,cls.web):threading.Thread(target=s.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        for s in (cls.web,cls.up):s.shutdown();s.server_close()
    def req(self,path='/',method='GET',headers=None,body=None):
        c=http.client.HTTPConnection('127.0.0.1',self.web.server_port)
        c.request(method,path,body,headers or {});r=c.getresponse();result=(r.status,r.read(),dict(r.getheaders()));c.close();return result
    def test_static_connected_script_and_no_file_exposure(self):
        self.assertEqual(self.req()[0],200)
        self.assertIn(b'PROOFLANE CONNECTED',self.req('/app.js')[1])
        self.assertEqual(self.req('/server.py')[0],404)
    def test_origin_csrf_cookie_and_body_forwarding(self):
        origin='http://127.0.0.1:'+str(self.web.server_port)
        status,_,headers=self.req('/api/auth/login','POST',{'Origin':origin,'X-CSRF-Token':'token','Content-Type':'application/json'},'{}')
        self.assertEqual(status,200)
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertEqual(Upstream.seen[-1],(proxy.PUBLIC_ORIGIN,'token',b'{}'))
    def test_cross_origin_host_and_missing_origin_blocked(self):
        self.assertEqual(self.req('/api/auth/login','POST',{'Origin':'http://evil.example'},'{}')[0],403)
        self.assertEqual(self.req('/api/auth/login','POST',{},'{}')[0],403)
        self.assertEqual(self.req('/',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.req('/api/auth/me',headers={'Sec-Fetch-Site':'cross-site'})[0],403)

if __name__=='__main__':unittest.main()
