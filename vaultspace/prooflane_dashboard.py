"""Loopback-only Vaultspace frontend proxy for the existing Prooflane API.
No AWS credentials, database, or scanner is loaded by this process.
"""
import http.client
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
UPSTREAM = urlsplit(os.environ.get('PROOFLANE_API_URL', 'http://127.0.0.1:8001'))
PUBLIC_ORIGIN = os.environ.get('PROOFLANE_PUBLIC_ORIGIN', 'http://localhost:5174')
if UPSTREAM.scheme != 'http' or UPSTREAM.hostname not in ('localhost', '127.0.0.1') or UPSTREAM.path not in ('', '/'):
    raise ValueError('Only a loopback HTTP API is supported.')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def error(self, status, message):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(json.dumps({'detail':message}).encode())

    def handle_request(self):
        allowed_hosts = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed_hosts:
            return self.error(403, 'Host rejected')
        path = urlsplit(self.path).path
        if path.startswith('/api/'):
            if self.command not in ('GET', 'POST', 'PATCH', 'DELETE'):
                return self.error(405, 'Method not allowed')
            origin = self.headers.get('Origin')
            expected_origin = 'http://' + self.headers['Host']
            if (origin and origin != expected_origin) or (self.command != 'GET' and origin != expected_origin):
                return self.error(403, 'Origin rejected')
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.error(403, 'Cross-site request rejected')
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 <= size <= 16*1024*1024:
                    return self.error(413, 'Request exceeds dashboard upload limit')
            except ValueError:
                return self.error(400, 'Invalid content length')
            headers = {k:self.headers[k] for k in ('Content-Type', 'Cookie', 'X-CSRF-Token', 'Accept') if self.headers.get(k)}
            # Translate only a validated same-origin request to the backend's configured origin.
            # CSRF token and session validation remain the backend's responsibility.
            if origin: headers['Origin'] = PUBLIC_ORIGIN
            connection = http.client.HTTPConnection(UPSTREAM.hostname, UPSTREAM.port or 80, timeout=100 if self.command == 'POST' and path == '/api/files' else 12)
            try:
                connection.request(self.command, self.path, self.rfile.read(size) if size else None, headers)
                response = connection.getresponse()
                content = response.read()
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() in ('content-type', 'content-disposition', 'set-cookie', 'x-content-type-options', 'referrer-policy'):
                        self.send_header(key, value)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Frame-Options', 'DENY')
                self.end_headers()
                self.wfile.write(content)
            except (OSError, http.client.HTTPException):
                self.error(502, 'Prooflane API unavailable. Check the existing hybrid launcher on port 8001. An upload timeout has an unknown outcome; refresh before retrying.')
            finally: connection.close()
            return
        if self.command != 'GET': return self.error(405, 'Method not allowed')
        assets = {'/':('index.html','text/html'), '/app.js':('prooflane.js','text/javascript'), '/style.css':('style.css','text/css')}
        if path not in assets: return self.error(404, 'Not found')
        filename, mime = assets[path]
        content = (ROOT / 'static' / filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime+'; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(content)

    do_GET = do_POST = do_PATCH = do_DELETE = handle_request

if __name__ == '__main__':
    port = int(os.environ.get('VAULT_DASHBOARD_PORT','8080'))
    httpd = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Vaultspace → Prooflane: http://localhost:{port} (API {UPSTREAM.geturl()})', flush=True)
    httpd.serve_forever()
