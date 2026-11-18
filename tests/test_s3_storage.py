"""Exact-version adapter contracts; AWS transport is an explicit test double."""
import importlib
from io import BytesIO
from types import SimpleNamespace
import pytest


@pytest.fixture
def adapter(monkeypatch):
    module = importlib.import_module('prooflane.storage')
    config = SimpleNamespace(environment='development', s3_endpoint=None, aws_region='us-east-1',
        s3_access_key='unused-minio-value', s3_secret_key='unused-minio-secret', s3_bucket='private-test',
        kms_key_id='alias/aws/s3', s3_bucket_key_enabled=True, max_upload_bytes=100)
    calls = []

    class Client:
        versioning = 'Enabled'
        version = 'immutable-test-version'

        def get_bucket_versioning(self, **kwargs):
            return {'Status': self.versioning}

        def put_object(self, **kwargs):
            calls.append(('put', kwargs))
            return {'VersionId': self.version}

        def get_object(self, **kwargs):
            calls.append(('get', kwargs))
            return {'Body': BytesIO(b'exact bytes')}

    client = Client()

    def factory(service, **options):
        calls.append(('client', options))
        assert service == 's3'
        return client

    monkeypatch.setattr(module, 'settings', lambda: config)
    monkeypatch.setattr(module.boto3, 'client', factory)
    return module.S3Storage(), client, calls


def test_hybrid_adapter_uses_chain_and_explicit_kms(adapter):
    storage, _, calls = adapter
    assert calls[0] == ('client', {'endpoint_url': None, 'region_name': 'us-east-1'})
    assert storage.put('tenant/object', BytesIO(b'content')) == 'immutable-test-version'
    request = calls[-1][1]
    assert request['ServerSideEncryption'] == 'aws:kms'
    assert 'SSEKMSKeyId' not in request  # S3 selects/creates aws/s3 on first use.
    assert request['BucketKeyEnabled'] is True


def test_s3_read_pins_the_requested_version(adapter):
    storage, _, calls = adapter
    assert storage.read('tenant/object', 'version-two') == b'exact bytes'
    assert calls[-1] == ('get', {'Bucket': 'private-test', 'Key': 'tenant/object', 'VersionId': 'version-two'})


@pytest.mark.parametrize('status', ['Suspended', None])
def test_upload_rejects_unversioned_bucket_before_write(adapter, status):
    storage, client, calls = adapter
    client.versioning = status
    with pytest.raises(RuntimeError, match='versioning must be enabled'):
        storage.put('tenant/object', BytesIO(b'content'))
    assert not any(kind == 'put' for kind, _ in calls)


@pytest.mark.parametrize('version', [None, '', 'null'])
def test_upload_rejects_missing_immutable_version(adapter, version):
    storage, client, _ = adapter
    client.version = version
    with pytest.raises(RuntimeError, match='Immutable version unavailable'):
        storage.put('tenant/object', BytesIO(b'content'))
