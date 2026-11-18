"""Credential routing and encryption regressions without AWS calls."""
from types import SimpleNamespace
import unittest

from prooflane.storage_options import client_options, encryption_options


def config(**overrides):
    values = dict(environment='development', s3_endpoint=None, aws_region='us-east-1',
                  s3_access_key='local-only', s3_secret_key='local-only-secret',
                  kms_key_id=None, s3_bucket_key_enabled=False)
    values.update(overrides)
    return SimpleNamespace(**values)


class StorageOptions(unittest.TestCase):
    def test_aws_hybrid_uses_sdk_chain_despite_legacy_minio_settings(self):
        result = client_options(config())
        self.assertEqual(result, {'endpoint_url': None, 'region_name': 'us-east-1'})
        self.assertNotIn('aws_access_key_id', result)
        self.assertNotIn('aws_secret_access_key', result)

    def test_explicit_local_endpoint_keeps_local_credentials(self):
        result = client_options(config(s3_endpoint='http://localhost:9000'))
        self.assertEqual(result['aws_access_key_id'], 'local-only')
        self.assertEqual(result['aws_secret_access_key'], 'local-only-secret')

    def test_production_never_injects_static_minio_credentials(self):
        # Runtime validation separately rejects custom endpoints in production.
        result = client_options(config(environment='production', s3_endpoint='http://localhost:9000'))
        self.assertNotIn('aws_access_key_id', result)
        self.assertNotIn('aws_secret_access_key', result)

    def test_aws_managed_kms_and_bucket_key_are_explicit(self):
        self.assertEqual(encryption_options(config(kms_key_id='alias/aws/s3', s3_bucket_key_enabled=True)), {
            'ServerSideEncryption': 'aws:kms', 'BucketKeyEnabled': True})

    def test_customer_managed_key_configuration_is_preserved(self):
        key = 'arn:aws:kms:us-east-1:123456789012:key/configured-key'
        self.assertEqual(encryption_options(config(kms_key_id=key)), {
            'ServerSideEncryption': 'aws:kms', 'SSEKMSKeyId': key})

    def test_local_storage_does_not_send_unsupported_encryption_options(self):
        self.assertEqual(encryption_options(config(s3_bucket_key_enabled=True)), {})


if __name__ == '__main__':
    unittest.main()
