#!/usr/bin/env python3
"""Local read-only startup diagnostics. No third-party dependencies required."""
import argparse
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def command(args, timeout=10):
    try:
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return result.returncode == 0, (result.stdout.strip() if result.returncode == 0 else result.stderr.strip() or result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)

def endpoint(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200, f'HTTP {response.status}'
    except (OSError, urllib.error.URLError) as error:
        return False, str(error)

def checks():
    results = []
    def add(name, ok, detail, required=True):
        results.append(dict(name=name, ok=ok, detail=detail, required=required))
    add('Configuration', (ROOT / '.env').is_file(), '.env exists' if (ROOT / '.env').is_file() else 'Run: python3 scripts/init_local_config.py')
    if shutil.which('docker'):
        ok, detail = command(['docker', 'info', '--format', '{{.ServerVersion}}'])
        add('Docker daemon', ok, detail)
        valid, detail = command(['docker', 'compose', '--env-file', 'config/local.example', 'config', '--quiet'])
        add('Compose configuration', valid, detail or 'Configuration is valid')
    else:
        add('Docker daemon', False, 'Install Docker with the Compose plugin and start its daemon')
    for hostname in ('registry.npmjs.org', 'pypi.org'):
        try:
            socket.getaddrinfo(hostname, 443)
            add(hostname, True, 'DNS resolution succeeded', False)
        except OSError as error:
            add(hostname, False, str(error), False)
    for name, url in [('Frontend', 'http://localhost:5173/'), ('API/database', 'http://localhost:8000/api/health')]:
        ok, detail = endpoint(url)
        add(name, ok, detail)
    add('Host frontend dependencies', (ROOT / 'apps/web/node_modules/.bin/vite').is_file(),
        'Required for host development; Compose installs these inside its build image', False)
    for package in ('fastapi', 'sqlalchemy', 'pytest'):
        available = importlib.util.find_spec(package) is not None
        add('Host Python: ' + package, available, 'Installed in this interpreter' if available else 'Not installed in this interpreter', False)
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    results = checks()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print('Prooflane local startup checks\n')
        for result in results:
            label = 'OK' if result['ok'] else 'FAIL' if result['required'] else 'NOTE'
            print(f"[{label}] {result['name']}: {result['detail']}")
        print('\nStart the stack with: ./scripts/start-local.sh')
        print('A refused connection means no accessible service is listening; refreshing the browser will not start it.')
    return int(any(not result['ok'] and result['required'] for result in results))

if __name__ == '__main__':
    sys.exit(main())
