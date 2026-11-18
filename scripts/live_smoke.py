#!/usr/bin/env python3
"""Exercise the real local stack; create an isolated smoke workspace.

No scanner doubles, direct DB mutations, Claude calls, or downloaded malware.
The optional EICAR check uses the standard harmless AV test pattern assembled
in memory, uploaded to private quarantine, and never executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.parse import urlparse
import uuid


def digest(data):
    return hashlib.sha256(data).hexdigest()


def eicar_pattern():
    # Split in source; assembled only for the intended antivirus check.
    payload = (b'X5O!P%@AP[4' + bytes([92]) + b'PZX54(P^)7CC)7}$' +
               b'EICAR-STANDARD-' + b'ANTIVIRUS-TEST-FILE!$H+H*')
    if len(payload) != 68:
        raise RuntimeError('EICAR test pattern length is incorrect')
    return payload


class API:
    def __init__(self, httpx, base, origin, upload_timeout=90):
        self.httpx = httpx
        self.upload_timeout = upload_timeout
        self.client = httpx.Client(base_url=base, timeout=30, trust_env=False,
                                   headers={'Origin': origin})

    def request(self, method, path, expected=200, **kwargs):
        started = time.monotonic()
        try:
            response = self.client.request(method, '/api' + path, **kwargs)
        except self.httpx.RequestError as error:
            # Do not echo the transport exception: it may include credentials,
            # request bodies or private storage URLs. Never retry a POST here.
            elapsed = time.monotonic() - started
            raise RuntimeError(f'{method} /api{path}: {type(error).__name__} after {elapsed:.1f}s; '
                               'request outcome is unconfirmed (no automatic retry)') from None
        allowed = (expected,) if isinstance(expected, int) else expected
        if response.status_code not in allowed:
            # Never echo a response body that could contain submitted credentials.
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}, expected {allowed}')
        return response

    def authenticate(self, action, email, password):
        result = self.request('POST', '/auth/' + action,
                              json={'email': email, 'password': password}).json()
        self.client.headers['X-CSRF-Token'] = result['csrf']
        return result['user']

    def upload(self, name, content, file_id=None):
        return self.request('POST', '/files',
                            params={'file_id': file_id} if file_id else {},
                            files={'file': (name, content, 'text/plain')},
                            timeout=self.httpx.Timeout(30, read=self.upload_timeout)).json()

    def download(self, version, expected=200):
        return self.request('GET', f"/files/{version['file_id']}/versions/{version['id']}/download", expected)

    def wait(self, version, target, timeout):
        end = time.monotonic() + timeout
        while True:
            details = self.request('GET', '/files/' + version['file_id']).json()
            current = next(v for v in details['versions'] if v['id'] == version['id'])
            if current['status'] == target:
                return details
            if current['status'] in ('FAILED', 'QUARANTINED', 'APPROVED'):
                raise RuntimeError(f"Version reached {current['status']} instead of {target}")
            if time.monotonic() >= end:
                raise RuntimeError(f"Worker timeout: version remains {current['status']}")
            time.sleep(2)


def verify_evidence(details, version, result):
    scans = [s for s in details['scans'] if s['version_id'] == version['id']]
    if not scans:
        raise RuntimeError('Exact-version scan evidence missing')
    scan = max(scans, key=lambda s: s['created'])
    if scan['result'] != result or scan['digest'] != version['digest'] or scan['object_version'] != version['object_version']:
        raise RuntimeError('Scan evidence does not match the requested version')
    if not scan['engine'].startswith('ClamAV ') or 'TEST DOUBLE' in scan['engine'].upper():
        raise RuntimeError('Real ClamAV engine/signature metadata is required')
    integrity = [i for i in details['integrity'] if i['version_id'] == version['id']]
    if not any(i['valid'] and i['baseline_digest'] == version['digest'] and
               i['observed_digest'] == version['digest'] for i in integrity):
        raise RuntimeError('Matching integrity evidence missing')
    return scan['engine']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://api:8000')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--upload-timeout', type=int, default=90, help='Per-upload response timeout in seconds; no POST retry')
    parser.add_argument('--output-dir', default='artifacts/live')
    parser.add_argument('--skip-eicar', action='store_true', help='Omit the harmless real-AV detection check')
    args = parser.parse_args()
    if not 1 <= args.upload_timeout <= 180:
        parser.error('--upload-timeout must be between 1 and 180 seconds')
    if os.environ.get('ENVIRONMENT', 'development') != 'development':
        parser.error('Live smoke checks are restricted to development')
    if urlparse(args.base_url).hostname not in ('api', 'web', 'localhost', '127.0.0.1', '::1'):
        parser.error('Use the local Compose API/web service or loopback address')
    import httpx
    origin = os.environ.get('PUBLIC_ORIGIN', 'http://localhost:5173')
    run = uuid.uuid4().hex
    report = {'run_id': run, 'kind': 'live local-stack smoke', 'started': time.time(),
              'checks': [], 'engines': [], 'resources': {}, 'status': 'running',
              'limitations': ['Not a concurrency stress test or malware-effectiveness study.',
                              'Creates a small isolated workspace and retains its test audit records.']}
    clients = []
    phase = 'initialization'

    def check(name):
        report['checks'].append({'name': name, 'passed': True})
        print('PASS ' + name, flush=True)

    def client():
        c = API(httpx, args.base_url, origin, args.upload_timeout);clients.append(c);return c

    start = time.monotonic()
    try:
        alice = client()
        phase = 'database-backed health'
        health = alice.request('GET', '/health').json()
        if health.get('database') != 'postgresql':
            raise RuntimeError('This check requires the real PostgreSQL stack')
        check('PostgreSQL-backed API health')
        phase = 'register isolated workspace'
        owner = alice.authenticate('register', f'smoke-{run}@example.invalid', secrets.token_urlsafe(24))
        report['resources']['tenant_id'] = owner['tenant_id']
        check('Registration and cookie authentication')

        phase = 'upload and actual verification'
        first = b'Prooflane live smoke version one.\n'
        v1 = alice.upload('live-smoke.txt', first)
        if v1['digest'] != digest(first):raise RuntimeError('Upload SHA-256 mismatch')
        # A worker may already have finished: do not fabricate a pending hold.
        early = alice.download(v1, (200, 423))
        report['pending_hold_observed'] = early.status_code == 423
        if early.status_code == 200 and early.content != first:raise RuntimeError('Early exact-version bytes mismatch')
        details = alice.wait(v1, 'APPROVED', args.timeout)
        report['engines'].append(verify_evidence(details, v1, 'CLEAN'))
        if alice.download(v1).content != first:raise RuntimeError('Exact-version download changed bytes')
        check('Real worker, ClamAV, version-bound SHA-256 evidence and download')

        phase = 'same-tenant sharing and revocation'
        bob_email = f'smoke-reader-{run}@example.invalid';bob_password = secrets.token_urlsafe(24)
        member = alice.request('POST', '/workspace/members', json={'email': bob_email, 'password': bob_password}).json()
        bob = client();bob.authenticate('login', bob_email, bob_password)
        bob.download(v1, 403)
        alice.request('POST', '/files/' + v1['file_id'] + '/share', json={'email': bob_email})
        bob.download(v1, 403)
        preview = bob.request('GET', f"/files/{v1['file_id']}/versions/{v1['id']}/preview")
        if preview.content != first:raise RuntimeError('Authorized shared preview changed bytes')
        alice.request('DELETE', f"/files/{v1['file_id']}/share/{member['id']}")
        bob.download(v1, 403)
        check('Unshared denial, view-only sharing, blocked shared download and post-revocation denial')

        phase = 'cross-tenant denial'
        outsider = client();outsider.authenticate('register', f'smoke-other-{run}@example.invalid', secrets.token_urlsafe(24))
        outsider.download(v1, 404)
        check('Cross-tenant access denial')

        phase = 'replacement and exact version selection'
        second = b'Prooflane live smoke version two, with different bytes.\n'
        v2 = alice.upload('live-smoke.txt', second, v1['file_id'])
        if v2['id'] == v1['id'] or v2['object_version'] == v1['object_version'] or v2['number'] != v1['number'] + 1:
            raise RuntimeError('Replacement did not create a separate object version')
        alice.download(v1, 423)
        details = alice.wait(v2, 'APPROVED', args.timeout)
        report['engines'].append(verify_evidence(details, v2, 'CLEAN'))
        if v2['digest'] != digest(second) or alice.download(v2).content != second:
            raise RuntimeError('Replacement version bytes or digest mismatch')
        check('New immutable version, old-target denial and exact V2 download')

        phase = 'real antivirus quarantine'
        if not args.skip_eicar:
            phase = 'antivirus test upload'
            print('CHECK Uploading harmless EICAR fixture (no automatic retry)', flush=True)
            av = alice.upload('live-antivirus-test.txt', eicar_pattern())
            report['resources']['antivirus_file_id'] = av['file_id']
            report['resources']['antivirus_version_id'] = av['id']
            phase = 'antivirus quarantine polling'
            print('CHECK Waiting for real ClamAV quarantine evidence', flush=True)
            details = alice.wait(av, 'QUARANTINED', args.timeout)
            phase = 'antivirus exact-version evidence'
            report['engines'].append(verify_evidence(details, av, 'INFECTED'))
            phase = 'quarantined download denial'
            alice.download(av, 423)
            check('Real ClamAV EICAR detection and quarantine download denial')
        else:
            report['skipped'] = ['Real antivirus EICAR detection check explicitly omitted']
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['failure'] = {'phase': phase, 'type': type(error).__name__, 'message': str(error)}
        print(f'FAIL {phase}: {error}', file=sys.stderr)
    finally:
        for c in clients:c.client.close()
        report['engines'] = sorted(set(report['engines']))
        report['elapsed_seconds'] = time.monotonic() - start
        out = Path(args.output_dir);out.mkdir(parents=True, exist_ok=True)
        destination = out / f'smoke-{run}.json';destination.write_text(json.dumps(report, indent=2))
        print('Report: ' + str(destination))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
