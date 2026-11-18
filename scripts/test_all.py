"""Run existing suites with separate logs and honest passed/failed/blocked status.

Requires the existing local stack, built API/research/cloud-check images and
installed web dependencies/Chromium for full coverage. No model retraining,
image builds, dependency installation or AWS resource creation is performed.
The authorized live Claude smoke requests one explanation, with at most one
extra billable format-repair request.
"""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    output = ROOT / 'artifacts' / 'test-runs' / run_id
    output.mkdir(parents=True)
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join([str(ROOT / 'apps/api'), str(ROOT)])
    results = []

    def blocked(name, reason):
        results.append({'name': name, 'status': 'blocked', 'reason': reason})
        print('BLOCKED ' + name + ': ' + reason, flush=True)

    def run(name, command, cwd=ROOT, timeout=600, env=None, browser=False):
        destination = output / (name + '.log')
        started = time.monotonic()
        try:
            with destination.open('w') as log:
                result = subprocess.run(command, cwd=cwd, env=env or environment,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
            status = 'passed' if code == 0 else 'failed'
            reason = None
            if browser and code:
                text = destination.read_text(errors='replace')
                if 'MachPortRendezvousServer' in text and 'Permission denied' in text:
                    status = 'blocked'; reason = 'OS sandbox denied Chromium Mach-port registration before navigation'
                elif "Executable doesn't exist" in text:
                    status = 'blocked'; reason = 'Playwright browser is not installed'
            row = {'name': name, 'status': status, 'exit_code': code,
                   'elapsed_seconds': time.monotonic() - started, 'log': str(destination.relative_to(ROOT))}
            if reason:
                row['reason'] = reason
            results.append(row)
            print(status.upper() + ' ' + name + ' (' + row['log'] + ')', flush=True)
        except (OSError, subprocess.TimeoutExpired) as error:
            results.append({'name': name, 'status': 'blocked' if isinstance(error, FileNotFoundError) else 'failed',
                            'reason': type(error).__name__, 'log': str(destination.relative_to(ROOT))})
            print('NOT COMPLETED ' + name + ': ' + type(error).__name__, flush=True)

    run('python-syntax', [sys.executable, '-m', 'compileall', '-q', 'apps/api', 'ml', 'benchmarks', 'scripts', 'tests'])
    run('stdlib-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', '*stdlib.py', '-v'])
    run('shell-syntax', ['sh', '-c', 'for prooflane_script in "$@"; do sh -n "$prooflane_script" || exit; done',
        'prooflane-shell-check', *[str(path.relative_to(ROOT)) for path in sorted((ROOT / 'scripts').glob('*.sh'))]])

    docker = shutil.which('docker')
    docker_available = False
    if docker:
        run('compose-configuration', [docker, 'compose', '--env-file', 'config/local.example', 'config', '--quiet'])
        try:
            with (output / 'docker-preflight.log').open('w') as log:
                docker_available = subprocess.run([docker, 'info', '--format', '{{.ServerVersion}}'],
                    stdout=log, stderr=subprocess.STDOUT, timeout=30).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        blocked('compose-configuration', 'Docker CLI is not installed')

    docker_checks = ['backend-pytest', 'research-pytest', 'aws-template-lint',
                     'live-security', 'live-models', 'live-claude']
    if not docker_available:
        for name in docker_checks:
            blocked(name, 'Docker daemon is inaccessible; see docker-preflight.log')
    else:
        # Bind current source/tests; keep configured keys out of unit-test environments.
        mounts = []
        for name in ('apps/api', 'ml', 'tests', 'scripts', 'benchmarks'):
            mounts += ['-v', str(ROOT / name) + ':/app/' + name + ':ro']
        base = [docker, 'compose', 'run', '--rm', '--no-deps', *mounts,
                '-e', 'ANTHROPIC_API_KEY=', '-e', 'ANTHROPIC_MODEL=']
        run('backend-pytest', [*base, 'api', 'python', '-m', 'pytest', '-q'], timeout=300)
        run('research-pytest', [docker, 'compose', '--profile', 'research', 'run', '--rm', '--no-deps', *mounts,
            '-e', 'ANTHROPIC_API_KEY=', '-e', 'ANTHROPIC_MODEL=', 'research',
            'python', '-m', 'pytest', 'tests/test_models.py', '-q', '-rs'], timeout=600)
        run('aws-template-lint', [docker, 'compose', '--profile', 'cloud-check', 'run', '--rm', '--no-deps',
            '-v', str(ROOT / 'infrastructure/aws') + ':/work/aws:ro', 'cloud-check'], timeout=180)
        run('live-security', [docker, 'compose', 'run', '--rm', '--no-deps', *mounts,
            'api', 'python', 'scripts/live_smoke.py'], timeout=600)
        run('live-models', ['sh', 'scripts/check-models.sh'], timeout=600)
        run('live-claude', ['sh', 'scripts/check-assistant.sh'], timeout=300)

    web = ROOT / 'apps/web'
    npm = shutil.which('npm')
    if npm and (web / 'node_modules/.bin/vite').exists():
        run('frontend-unit', [npm, 'run', 'test:unit'], cwd=web, timeout=180)
        run('frontend-build', [npm, 'run', 'build'], cwd=web, timeout=180)
        browser_env = environment.copy()
        browser_env['E2E_OUTPUT_DIR'] = str(output / 'browser')
        browser_env['E2E_JSON_REPORT'] = str(output / 'browser-report.json')
        run('browser-e2e', [npm, 'run', 'test:e2e'], cwd=web, timeout=660, env=browser_env, browser=True)
    else:
        blocked('frontend-unit', 'Install the existing web dependencies with npm ci')
        blocked('frontend-build', 'Install the existing web dependencies with npm ci')
        blocked('browser-e2e', 'Web dependencies and Playwright Chromium are required')

    summary = {status: sum(row['status'] == status for row in results) for status in ('passed', 'failed', 'blocked')}
    report = {'run_id': run_id, 'checks': results, 'summary': summary,
              'all_passed': not summary['failed'] and not summary['blocked'],
              'limitations': ['Runs existing suites; a pass does not establish full research or production acceptance.',
                              'Live checks create isolated development test records; Claude smoke uses the configured provider.',
                              'Does not retrain models, run a multi-seed study or provision AWS infrastructure.']}
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    print('Summary: ' + json.dumps(summary), flush=True)
    print('Report: ' + str((output / 'report.json').relative_to(ROOT)), flush=True)
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
