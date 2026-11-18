#!/usr/bin/env python3
"""Check genuine model-backed decisions and real antivirus release enforcement.

Creates one isolated development workspace, selects each model there, and
retains the small uploaded fixtures/audit records. No model training, database
mutation, scanner doubles, Claude requests or AWS calls are performed.
"""
import argparse
import math
import os
from pathlib import Path
import json
import secrets
import sys
import time
from urllib.parse import urlparse
import uuid

if __package__:
    from .live_smoke import API, digest, eicar_pattern, verify_evidence
else:
    from live_smoke import API, digest, eicar_pattern, verify_evidence


def validate_decision(job, decision, method, model_version):
    """Reject a deterministic fallback or an unbound/non-finite model result."""
    inputs = decision.get('inputs', {})
    prediction = inputs.get('prediction')
    if job['status'] != 'COMPLETE' or decision['job_id'] != job['id']:
        raise ValueError('The decision must reference the completed verification job')
    if decision['strategy'] != method or inputs.get('fallback') is not None:
        raise ValueError('The worker used a fallback instead of the requested model')
    if inputs.get('model_version') != model_version:
        raise ValueError('Worker checkpoint differs from the validated API checkpoint')
    if not isinstance(prediction, (list, tuple)) or len(prediction) != 2:
        raise ValueError('Both workload prediction heads must be recorded')
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0 for v in prediction):
        raise ValueError('Invalid workload prediction')
    if inputs.get('feature_schema') != 2 or len(inputs.get('features', [])) != 8:
        raise ValueError('Scheduling-time feature snapshot is missing')
    return {'job_id': job['id'], 'version_id': job['version_id'],
            'strategy': method, 'model_version': model_version,
            'prediction': prediction, 'scheduler_seconds': inputs.get('scheduler_seconds'),
            'constraints': inputs.get('constraints', [])}


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
    report = {'run_id': run, 'kind': 'live trained-model integration smoke',
              'checks': [], 'decisions': [], 'engines': [], 'status': 'running',
              'limitations': ['Small functional check, not a ranking-quality or latency benchmark.',
                              'Synthetic-trained checkpoints; no real-world efficacy claim.',
                              'Creates one isolated workspace and retains its test records.']}
    start = time.monotonic()
    api = API(httpx, args.base_url, os.environ.get('PUBLIC_ORIGIN', 'http://localhost:5173'))
    phase = 'health and model availability'
    try:
        if api.request('GET', '/health').json().get('database') != 'postgresql':
            raise RuntimeError('Requires the real PostgreSQL-backed stack')
        user = api.authenticate('register', f'ml-smoke-{run}@example.invalid', secrets.token_urlsafe(24))
        report['tenant_id'] = user['tenant_id']
        models = {m['name']: m for m in api.request('GET', '/research/models').json()}
        for method in ('lightgbm', 'tgn'):
            if not models.get(method, {}).get('available'):
                raise RuntimeError(f'{method}: no compatible trained checkpoint')
            phase = method + ' real worker decisions'
            api.request('POST', '/scheduler/strategy', json={'strategy': method})
            versions = []
            for index in range(3):
                content = f'Harmless {method} integration fixture {index}.\n'.encode()
                versions.append((api.upload(f'{method}-{index}.txt', content), content, 'APPROVED'))
            versions.append((api.upload(f'{method}-antivirus-test.txt', eicar_pattern()), None, 'QUARANTINED'))
            for version, content, expected in versions:
                details = api.wait(version, expected, args.timeout)
                report['engines'].append(verify_evidence(details, version, 'CLEAN' if content is not None else 'INFECTED'))
                if content is None:
                    api.download(version, 423)
                elif version['digest'] != digest(content) or api.download(version).content != content:
                    raise RuntimeError('Approved exact-version bytes/digest mismatch')
            state = api.request('GET', '/scheduler').json()
            for version, _, _ in versions:
                jobs = [j for j in state['jobs'] if j['version_id'] == version['id'] and j['status'] == 'COMPLETE']
                if not jobs:
                    raise RuntimeError('Completed verification job not recorded')
                job = max(jobs, key=lambda j: j['completed'])
                decisions = [d for d in state['decisions'] if d['job_id'] == job['id']]
                if not decisions:
                    raise RuntimeError('Model-backed scheduling decision not recorded')
                decision = max(decisions, key=lambda d: d['created'])
                report['decisions'].append(validate_decision(job, decision, method, models[method]['model_version']))
            name = f'{method}: real checkpoint predictions, clean exact downloads and EICAR release denial'
            report['checks'].append({'name': name, 'passed': True})
            print('PASS ' + name, flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['failure'] = {'phase': phase, 'type': type(error).__name__, 'message': str(error)}
        print(f'FAIL {phase}: {error}', file=sys.stderr)
    finally:
        api.client.close()
        report['elapsed_seconds'] = time.monotonic() - start
        report['engines'] = sorted(set(report['engines']))
        out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
        destination = out / f'ml-smoke-{run}.json'
        destination.write_text(json.dumps(report, indent=2))
        print('Report: ' + str(destination))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
