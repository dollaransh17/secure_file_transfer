#!/usr/bin/env python3
"""Test one real Claude explanation and permission-filtered evidence locally.

Creates isolated development accounts and one harmless EICAR antivirus fixture.
Makes one short Claude explanation through the application's official SDK
integration, with at most one extra billable format-repair request. Never sends
file bytes or credentials to the model. No AWS calls.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.parse import urlparse
import uuid

if __package__:
    from .live_smoke import API, eicar_pattern, verify_evidence
else:
    from live_smoke import API, eicar_pattern, verify_evidence


def validate_answer(response, authorized_ids, version_id):
    if response.get('status') != 'answered':
        raise ValueError('Claude did not return a validated answer: ' + str(response.get('status')))
    events = response.get('events', [])
    ids = {event['id'] for event in events}
    if not ids or not ids.issubset(authorized_ids):
        raise ValueError('Answer contains unauthorized or unknown event records')
    if not any(event.get('version') == version_id for event in events):
        raise ValueError('Expected file-version evidence missing')
    refs = set(re.findall(r'\[([0-9a-f-]{36})\]', response.get('answer', '')))
    if not refs or not refs.issubset(ids):
        raise ValueError('Answer contains missing or unknown event citations')
    usage = response.get('usage', {})
    if any(type(usage.get(key)) is not int or usage[key] <= 0 for key in ('input_tokens', 'output_tokens')):
        raise ValueError('Actual provider token usage is required')


def validate_no_evidence(response):
    if response.get('events') or response.get('usage') or response.get('status') != 'evidence_only':
        raise ValueError('Inaccessible evidence must not be retrieved or sent to Claude')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://api:8000')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--output-dir', default='artifacts/live')
    args = parser.parse_args()
    if os.environ.get('ENVIRONMENT', 'development') != 'development':
        parser.error('Live smoke checks are restricted to development')
    if urlparse(args.base_url).hostname not in ('api', 'web', 'localhost', '127.0.0.1', '::1'):
        parser.error('Use the local Compose API/web service or loopback address')
    import httpx
    run = uuid.uuid4().hex
    report = {'run_id': run, 'kind': 'live Claude authorized-evidence smoke',
              'status': 'running', 'checks': [],
              'limitations': ['Citation identifiers and permissions are checked; semantic entailment is not proven.',
                              'One generated explanation is not an adversarial RAG evaluation.',
                              'Creates one small isolated workspace and an outside account; retains test records.']}
    clients = []
    start = time.monotonic()
    phase = 'configuration'

    def client():
        item = API(httpx, args.base_url, os.environ.get('PUBLIC_ORIGIN', 'http://localhost:5173'))
        item.client.timeout = httpx.Timeout(65)
        clients.append(item)
        return item

    def check(name):
        report['checks'].append({'name': name, 'passed': True})
        print('PASS ' + name, flush=True)

    try:
        owner = client()
        if owner.request('GET', '/health').json().get('database') != 'postgresql':
            raise RuntimeError('Requires the real PostgreSQL-backed stack')
        user = owner.authenticate('register', f'assistant-smoke-{run}@example.invalid', secrets.token_urlsafe(24))
        report['tenant_id'] = user['tenant_id']
        config = owner.request('GET', '/assistant/status').json()
        if not config.get('configured'):
            raise RuntimeError('Claude is not configured in the running API; recreate it after setting .env')
        report['model'] = config['model']
        phase = 'real security evidence'
        version = owner.upload('assistant-antivirus-test.txt', eicar_pattern())
        details = owner.wait(version, 'QUARANTINED', args.timeout)
        report['engine'] = verify_evidence(details, version, 'INFECTED')
        owner.download(version, 423)
        question = f'Why was version {version["id"]} quarantined and its download denied? Explain only recorded events and cite their identifiers.'
        phase = 'cross-tenant evidence denial'
        outside = client()
        outside.authenticate('register', f'assistant-outside-{run}@example.invalid', secrets.token_urlsafe(24))
        validate_no_evidence(outside.request('POST', '/assistant', json={'question': question}).json())
        check('Cross-tenant evidence excluded without a generation call')
        phase = 'authorized Claude explanation'
        email = f'assistant-reader-{run}@example.invalid'; password = secrets.token_urlsafe(24)
        member = owner.request('POST', '/workspace/members', json={'email': email, 'password': password}).json()
        reader = client(); reader.authenticate('login', email, password)
        owner.request('POST', f'/files/{version["file_id"]}/share', json={'email': email})
        authorized = {event['id'] for event in owner.request('GET', f'/files/{version["file_id"]}').json()['events']}
        response = reader.request('POST', '/assistant', json={'question': question}).json()
        validate_answer(response, authorized, version['id'])
        report['explanation'] = response
        check('Real Claude answer cites only authorized recorded events and reports actual token usage')
        phase = 'revoked evidence denial'
        owner.request('DELETE', f'/files/{version["file_id"]}/share/{member["id"]}')
        validate_no_evidence(reader.request('POST', '/assistant', json={'question': question}).json())
        reader.download(version, 403)
        check('Revocation removes assistant evidence and denies new downloads')
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['failure'] = {'phase': phase, 'type': type(error).__name__, 'message': str(error)}
        print(f'FAIL {phase}: {error}', file=sys.stderr)
    finally:
        for item in clients:
            item.client.close()
        report['elapsed_seconds'] = time.monotonic() - start
        out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
        path = out / f'assistant-smoke-{run}.json'
        path.write_text(json.dumps(report, indent=2))
        print('Report: ' + str(path))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
