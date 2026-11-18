"""Hybrid preflight safeguards. All cloud clients below are explicit doubles."""
import json
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.start_hybrid import cloud_preflight, run_local_step, server_environment, validate_config, validate_identity


def config(**changes):
    values = dict(ENVIRONMENT='development', STORAGE_BACKEND='s3', S3_ENDPOINT='',
        S3_BUCKET='prooflane-test', KMS_KEY_ID='alias/aws/s3', S3_BUCKET_KEY_ENABLED='true',
        AWS_REGION='ap-south-1', STORAGE_EVENT_QUEUE_URL='https://sqs.ap-south-1.amazonaws.com/123456789012/events',
        DATABASE_URL='postgresql+psycopg://prooflane:example@localhost:15432/prooflane', REDIS_URL='redis://localhost:16379/0',
        PUBLIC_ORIGIN='http://localhost:5174', PROOFLANE_DEV_API_URL='http://127.0.0.1:8001', DATABASE_HOST='', REDIS_HOST='')
    return {**values, **changes}


class HybridStartup(unittest.TestCase):
    def test_docker_engine_failure_gives_action_without_echoing_diagnostics(self):
        command = ['docker', 'version', '--format', '{{.Server.Version}}']
        failure = subprocess.CalledProcessError(1, command, stderr=b'sensitive-diagnostic')
        with patch('scripts.start_hybrid.subprocess.run', side_effect=failure), self.assertRaises(RuntimeError) as caught:
            run_local_step('Checking local Docker engine', command, capture_output=True, timeout=20)
        self.assertIn('Docker Desktop', str(caught.exception))
        self.assertIn('docker version', str(caught.exception))
        self.assertNotIn('sensitive-diagnostic', str(caught.exception))

    def test_compose_and_migration_failures_identify_distinct_stages(self):
        for label, command in [('Starting local services', ['docker', 'compose', 'up']),
                               ('Migrating local PostgreSQL database', ['python', '-m', 'alembic', 'upgrade', 'head'])]:
            with self.subTest(label=label):
                failure = subprocess.CalledProcessError(2, command)
                with patch('scripts.start_hybrid.subprocess.run', side_effect=failure), self.assertRaises(RuntimeError) as caught:
                    run_local_step(label, command)
                self.assertIn(label+' failed (exit 2)', str(caught.exception))

    def test_local_step_handles_missing_docker_and_timeout(self):
        for failure, expected in [(FileNotFoundError(), 'executable is unavailable (docker)'),
                                  (subprocess.TimeoutExpired(['docker', 'info'], 20), 'timed out')]:
            with self.subTest(expected=expected):
                with patch('scripts.start_hybrid.subprocess.run', side_effect=failure), self.assertRaisesRegex(RuntimeError, expected.replace('(', r'\(').replace(')', r'\)')):
                    run_local_step('Checking local Docker engine', ['docker', 'info'])

    def test_wrong_principals_cannot_pass_identity_check(self):
        for arn, account in [('arn:aws:iam::123456789012:root', '123456789012'),
                             ('arn:aws:iam::123456789012:user/prooflane-api', '123456789012'),
                             ('arn:aws:iam::000000000000:user/prooflane-worker', '000000000000')]:
            with self.subTest(arn=arn), self.assertRaises(RuntimeError):
                validate_identity({'Account': account, 'Arn': arn}, '123456789012', 'worker')

    def test_runtime_env_drops_shell_credentials_and_uses_worker_profile(self):
        with patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': 'stale', 'AWS_SECRET_ACCESS_KEY': 'stale',
                                      'AWS_SESSION_TOKEN': 'stale', 'AWS_DEFAULT_PROFILE': 'default'}):
            environment = server_environment(config(AWS_PROFILE='default'), 'prooflane-worker')
        self.assertEqual(environment['AWS_PROFILE'], 'prooflane-worker')
        self.assertEqual(environment['AWS_DEFAULT_PROFILE'], 'prooflane-worker')
        self.assertFalse({'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN'} & environment.keys())

    def test_unsafe_or_incomplete_hybrid_configuration_is_rejected(self):
        for changes in [dict(S3_ENDPOINT='http://minio:9000'), dict(ENVIRONMENT='production'),
                        dict(STORAGE_BACKEND='local'), dict(KMS_KEY_ID=''), dict(S3_BUCKET_KEY_ENABLED='false'),
                        dict(DATABASE_URL='sqlite:///test.db'), dict(PUBLIC_ORIGIN='http://0.0.0.0:5174'),
                        dict(DATABASE_URL='postgresql+psycopg://test:example@remote:5432/prooflane'),
                        dict(DATABASE_URL='postgresql+psycopg://prooflane:example@localhost:15432/old-database'),
                        dict(CLAMAV_HOST='remote-scanner'),
                        dict(STORAGE_EVENT_QUEUE_URL='http://sqs.ap-south-1.amazonaws.com/123456789012/events'),
                        dict(STORAGE_EVENT_QUEUE_URL='https://evil.test/123456789012/events'),
                        dict(DATABASE_URL='REPLACE_WITH_PASSWORD'), dict(DATABASE_HOST='cloud.internal')]:
            with self.subTest(fields=list(changes)), self.assertRaises(RuntimeError):
                validate_config(config(**changes))

    def run_cloud(self, *, wrong_worker=False, versioning='Enabled', encrypted='true', redrive=True):
        calls = []

        class Client:
            def __init__(self, profile, service):
                self.profile, self.service = profile, service

            def get_caller_identity(self):
                calls.append(('identity', self.profile))
                name = 'api' if wrong_worker or self.profile == 'prooflane-api' else 'worker'
                return {'Account': '123456789012', 'Arn': 'arn:aws:iam::123456789012:user/prooflane-'+name}

            def get_bucket_versioning(self, **kwargs):
                calls.append(('versioning', self.profile))
                return {'Status': versioning}

            def get_queue_attributes(self, **kwargs):
                calls.append(('queue', self.profile))
                policy = {'maxReceiveCount': 5, 'deadLetterTargetArn': 'arn:aws:sqs:ap-south-1:123456789012:dead'} if redrive else {}
                return {'Attributes': {'SqsManagedSseEnabled': encrypted, 'VisibilityTimeout': '180', 'RedrivePolicy': json.dumps(policy)}}

        try:
            cloud_preflight(config(), factory=Client)
            return None, calls
        except RuntimeError as error:
            return error, calls

    def test_api_identity_in_worker_profile_fails_before_storage_checks(self):
        error, calls = self.run_cloud(wrong_worker=True)
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual([kind for kind, _ in calls], ['identity', 'identity'])

    def test_disabled_versioning_stops_queue_and_startup(self):
        error, calls = self.run_cloud(versioning='Suspended')
        self.assertIsInstance(error, RuntimeError)
        self.assertNotIn('queue', [kind for kind, _ in calls])

    def test_missing_queue_encryption_or_redrive_blocks_startup(self):
        for changes in [dict(encrypted='false'), dict(redrive=False)]:
            with self.subTest(changes=changes):
                error, _ = self.run_cloud(**changes)
                self.assertIsInstance(error, RuntimeError)

    def test_valid_preflight_uses_expected_components(self):
        error, calls = self.run_cloud()
        self.assertIsNone(error)
        self.assertEqual(calls, [('identity', 'prooflane-api'), ('identity', 'prooflane-worker'),
                                 ('versioning', 'prooflane-api'), ('queue', 'prooflane-worker')])

    def test_missing_profile_is_rejected_before_any_cloud_client(self):
        fake = SimpleNamespace(Session=lambda: SimpleNamespace(available_profiles=['prooflane-api']))
        with patch.dict('sys.modules', {'boto3': fake}), self.assertRaisesRegex(RuntimeError, 'Missing runtime profile'):
            cloud_preflight(config())

    def test_provider_failure_names_the_profile_without_echoing_diagnostics(self):
        def broken(profile, service):
            raise ValueError('sensitive-provider-diagnostic')

        with self.assertRaises(RuntimeError) as caught:
            cloud_preflight(config(), factory=broken)
        self.assertIn('prooflane-api', str(caught.exception))
        self.assertIn('ValueError', str(caught.exception))
        self.assertNotIn('sensitive-provider-diagnostic', str(caught.exception))

    def test_missing_export_region_identifies_source_profile_without_exposing_output(self):
        def broken(profile, service):
            raise ValueError('You must specify a region. sensitive-provider-diagnostic')

        with self.assertRaises(RuntimeError) as caught:
            cloud_preflight(config(), factory=broken)
        self.assertIn('aws configure set region ap-south-1 --profile prooflane-api-login', str(caught.exception))
        self.assertNotIn('sensitive-provider-diagnostic', str(caught.exception))

    def test_expired_session_names_login_profile_without_exposing_output(self):
        def broken(profile, service):
            raise ValueError('Your session has expired. sensitive-provider-diagnostic')

        with self.assertRaises(RuntimeError) as caught:
            cloud_preflight(config(), factory=broken)
        self.assertIn('aws login --profile prooflane-api-login --region ap-south-1', str(caught.exception))
        self.assertNotIn('sensitive-provider-diagnostic', str(caught.exception))
