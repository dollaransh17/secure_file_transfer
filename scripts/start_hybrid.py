"""Run the local app against the existing AWS stack. Creates no AWS resources."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import unquote, urlparse
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'api': 'prooflane-api', 'worker': 'prooflane-worker'}
DIRECT_CREDENTIALS = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN')


def validate_config(values):
    if any('REPLACE_WITH_' in str(value) for value in values.values()):
        raise RuntimeError('Complete the placeholders in artifacts/aws-hybrid.env first.')
    if values.get('ENVIRONMENT') != 'development' or values.get('STORAGE_BACKEND') != 's3':
        raise RuntimeError('This launcher requires explicit development mode and S3 storage.')
    if values.get('S3_ENDPOINT') or values.get('KMS_KEY_ID') != 'alias/aws/s3' or values.get('S3_BUCKET_KEY_ENABLED') != 'true':
        raise RuntimeError('Hybrid storage requires the AWS endpoint, aws/s3 encryption and Bucket Keys.')
    queue = urlparse(values.get('STORAGE_EVENT_QUEUE_URL', ''))
    parts = queue.path.strip('/').split('/')
    region = values.get('AWS_REGION', '')
    if (queue.scheme != 'https' or queue.netloc != f'sqs.{region}.amazonaws.com' or
            len(parts) != 2 or len(parts[0]) != 12 or not parts[0].isdigit() or not parts[1] or queue.query or queue.fragment):
        raise RuntimeError('Set the exact AWS source queue URL and matching region from stack outputs.')
    for field in ('DATABASE_URL', 'REDIS_URL', 'PUBLIC_ORIGIN', 'PROOFLANE_DEV_API_URL'):
        if urlparse(values.get(field, '')).hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise RuntimeError(f'{field} must point to local services for this hybrid launcher.')
    if not values['DATABASE_URL'].startswith('postgresql+psycopg://'):
        raise RuntimeError('Hybrid verification requires the local PostgreSQL database.')
    database = urlparse(values['DATABASE_URL'])
    if database.username != 'prooflane' or database.path != '/prooflane' or not database.password or not database.port:
        raise RuntimeError('Use the isolated Compose database/user prooflane with an explicit local port and password.')
    if values.get('CLAMAV_HOST', 'localhost') not in ('127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('The ClamAV scanner must stay local in this hybrid setup.')
    for field in ('PUBLIC_ORIGIN', 'PROOFLANE_DEV_API_URL'):
        target = urlparse(values[field])
        if target.scheme != 'http' or not target.port:
            raise RuntimeError(f'{field} requires an explicit loopback HTTP port in development.')
    if values.get('DATABASE_HOST') or values.get('REDIS_HOST'):
        raise RuntimeError('Clear cloud database/cache host overrides in hybrid mode.')
    return parts[0]


def validate_identity(identity, account, component):
    expected = f'arn:aws:iam::{account}:user/prooflane-{component}'
    if identity.get('Account') != account or identity.get('Arn') != expected:
        raise RuntimeError(f'{PROFILES[component]} must resolve to IAM user prooflane-{component} in the storage account. Correct its login before startup.')


def server_environment(values, profile):
    environment = {**os.environ, **{key: str(value) for key, value in values.items() if value is not None}}
    # Explicit process-profile authentication; stale shell access keys must not
    # override it in Boto3's default credential chain.
    for key in DIRECT_CREDENTIALS:
        environment.pop(key, None)
    environment['AWS_PROFILE'] = profile
    environment['AWS_DEFAULT_PROFILE'] = profile
    return environment


def cloud_preflight(values, factory=None):
    account = validate_config(values)
    if factory is None:
        import boto3
        missing = set(PROFILES.values()) - set(boto3.Session().available_profiles)
        if missing:
            raise RuntimeError('Missing runtime profile(s): '+', '.join(sorted(missing))+'. Configure the process-credential bridges in infrastructure/aws/RUNTIME_ACCESS.md first.')
        from botocore.config import Config
        options = Config(connect_timeout=5, read_timeout=10, retries={'total_max_attempts': 1})

        def factory(profile, service):
            return boto3.Session(profile_name=profile, region_name=values['AWS_REGION']).client(service, config=options)

    # Check both principals before any storage/queue call or local startup.
    for component, profile in PROFILES.items():
        try:
            identity = factory(profile, 'sts').get_caller_identity()
        except Exception as error:
            # A credential-process error can contain subprocess diagnostics.
            # Match known causes, but never echo raw provider output or tokens.
            diagnostic = str(error).lower()
            region = values['AWS_REGION']
            login_profile = profile+'-login'
            if 'you must specify a region' in diagnostic:
                recovery = (f'The credential-export subprocess has no region. Run: '
                            f'aws configure set region {region} --profile {login_profile}')
            elif 'session has expired' in diagnostic or 'refresh token has expired' in diagnostic:
                recovery = f'Renew the matching IAM session: aws login --profile {login_profile} --region {region}'
            elif 'could not connect to the endpoint url' in diagnostic:
                recovery = 'The AWS endpoint could not be reached. Check network access in your host Terminal.'
            else:
                recovery = f'In your host Terminal run: aws sts get-caller-identity --profile {profile} --region {region}'
            raise RuntimeError(f'{profile}: AWS identity check failed ({type(error).__name__}). {recovery}') from None
        validate_identity(identity, account, component)
    versioning = factory(PROFILES['api'], 's3').get_bucket_versioning(Bucket=values['S3_BUCKET'])
    if versioning.get('Status') != 'Enabled':
        raise RuntimeError('AWS bucket versioning is not enabled; refusing startup.')
    attributes = factory(PROFILES['worker'], 'sqs').get_queue_attributes(
        QueueUrl=values['STORAGE_EVENT_QUEUE_URL'],
        AttributeNames=['SqsManagedSseEnabled', 'RedrivePolicy', 'VisibilityTimeout'])['Attributes']
    redrive = json.loads(attributes.get('RedrivePolicy', '{}'))
    if (attributes.get('SqsManagedSseEnabled') != 'true' or attributes.get('VisibilityTimeout') != '180' or
            int(redrive.get('maxReceiveCount', 0)) != 5 or
            not redrive.get('deadLetterTargetArn', '').startswith(f'arn:aws:sqs:{values["AWS_REGION"]}:{account}:')):
        raise RuntimeError('Source queue encryption, visibility or dead-letter settings do not match the reviewed stack.')


def wait_health(url, processes, timeout=90):
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(process.poll() is not None for _, process in processes):
            raise RuntimeError('A local process exited. Inspect .runtime/hybrid/*.log.')
        try:
            with opener.open(url, timeout=2) as response:
                status = json.loads(response.read(4096))
            if status.get('status') == 'ok' and status.get('database') == 'postgresql':
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError('Timed out waiting for the PostgreSQL-backed API/proxy. Inspect .runtime/hybrid/*.log.')


def run_local_step(label, command, *, environment=None, capture_output=False, timeout=None):
    """Name failed startup stages without echoing command environments/diagnostics."""
    print(label+'...', flush=True)
    try:
        return subprocess.run(command, cwd=ROOT, env=environment, check=True,
                              capture_output=capture_output, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(f'{label} failed: required executable is unavailable ({Path(command[0]).name}).') from None
    except subprocess.TimeoutExpired:
        hint = (' Docker Desktop is not responding to the engine check. '
                'Check Docker Desktop; if it remains stuck, restart it when other container work can be interrupted. '
                'Then verify: docker version --format "{{.Server.Version}}"'
                if command[:2] in (['docker', 'info'], ['docker', 'version']) else
                ' Check the local service and retry startup.')
        raise RuntimeError(f'{label} timed out.'+hint) from None
    except subprocess.CalledProcessError as error:
        message = f'{label} failed (exit {error.returncode}).'
        if command[:2] in (['docker', 'info'], ['docker', 'version']):
            message += (' Docker Desktop must be running and accessible from this Terminal. '
                        'Open Docker Desktop, wait until its engine is running, then run: docker version --format "{{.Server.Version}}"')
        elif 'compose' in command[:2]:
            message += ' Review the Compose error above; check local ports and container health.'
        elif command[0] == 'npm':
            message += ' Review the frontend build error above.'
        else:
            message += ' Review the migration error above.'
        raise RuntimeError(message) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check identities, versioning and queue settings without launching services')
    args = parser.parse_args()
    processes = []
    try:
        from dotenv import dotenv_values
        private = ROOT / 'artifacts/aws-hybrid.env'
        if not private.is_file():
            raise RuntimeError('Prepare artifacts/aws-hybrid.env from the hybrid example and stack outputs first.')
        base = {key: value for key, value in dotenv_values(ROOT/'.env').items() if value is not None}
        values = {**base, **dict(dotenv_values(private))}
        cloud_preflight(values)
        print('PASS expected API/worker identities, AWS bucket versioning and encrypted SQS/DLQ settings', flush=True)
        if args.check:
            return 0
        api = urlparse(values['PROOFLANE_DEV_API_URL'])
        web = urlparse(values['PUBLIC_ORIGIN'])
        for port in (api.port, web.port):
            with socket.socket() as probe:
                probe.settimeout(1)
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    raise RuntimeError(f'Loopback port {port} is occupied. Stop the old Prooflane listener or choose matching free ports; no processes were stopped.')
        api_env = server_environment(values, PROFILES['api'])
        worker_env = server_environment(values, PROFILES['worker'])
        database = urlparse(values['DATABASE_URL'])
        # Match the isolated infrastructure ports/password to the private URL.
        api_env['POSTGRES_DEV_PORT'] = str(database.port)
        api_env['POSTGRES_PASSWORD'] = unquote(database.password)
        api_env['REDIS_DEV_PORT'] = str(urlparse(values['REDIS_URL']).port or 16379)
        api_env['CLAMAV_DEV_PORT'] = str(int(values.get('CLAMAV_PORT', '13310')))
        # Query the server version without collecting the full daemon info report.
        run_local_step('Checking local Docker engine', ['docker', 'version', '--format', '{{.Server.Version}}'], capture_output=True, timeout=20)
        run_local_step('Starting local PostgreSQL, Redis and ClamAV', ['docker', 'compose', '-p', 'prooflane-hybrid', '-f', 'docker-compose.yml', '-f', 'docker-compose.dev.yml',
                        'up', '-d', '--wait', '--wait-timeout', '600', 'postgres', 'redis', 'clamav'],
                       environment=api_env)
        run_local_step('Migrating local PostgreSQL database', [sys.executable, '-m', 'alembic', 'upgrade', 'head'], environment=api_env)
        logs = ROOT/'.runtime/hybrid'
        logs.mkdir(parents=True, exist_ok=True, mode=0o700)

        def start(name, command, environment):
            descriptor = os.open(logs/(name+'.log'), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, 'w') as log:
                process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append((name, process))

        start('api', [sys.executable, '-m', 'uvicorn', 'prooflane.main:app', '--host', '127.0.0.1', '--port', str(api.port)], api_env)
        wait_health(values['PROOFLANE_DEV_API_URL']+'/api/health', processes)
        for number in (1, 2):
            start('worker-'+str(number), [sys.executable, '-m', 'prooflane.worker'], worker_env)
        # Backend secrets and credentials are not passed to the frontend process.
        front_env = {key: value for key, value in os.environ.items() if key in
                     ('PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM')}
        front_env['PROOFLANE_DEV_API_URL'] = values['PROOFLANE_DEV_API_URL']
        # Exercise the built frontend, as the Docker UI does. Avoid on-demand
        # module transforms and development reloads during live browser checks.
        run_local_step('Building local frontend', ['npm', '--prefix', 'apps/web', 'run', 'build'], environment=front_env)
        start('web', ['npm', '--prefix', 'apps/web', 'run', 'preview', '--', '--host', '127.0.0.1', '--port', str(web.port), '--strictPort'], front_env)
        wait_health(values['PUBLIC_ORIGIN']+'/api/health', processes)
        print('Prooflane AWS hybrid ready: '+values['PUBLIC_ORIGIN'], flush=True)
        print('API and two workers use separate IAM identities. Logs: .runtime/hybrid/*.log', flush=True)
        print('Ctrl+C stops these host processes. Local infrastructure and retained AWS resources remain.', flush=True)
        while True:
            if any(process.poll() is not None for _, process in processes):
                raise RuntimeError('A hybrid process exited. Inspect .runtime/hybrid/*.log.')
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        print(f'Hybrid startup failed ({type(error).__name__}). Check runtime profiles, AWS login/network and local Docker. No root fallback is used.', file=sys.stderr)
        return 1
    finally:
        for _, process in reversed(processes):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        for _, process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
