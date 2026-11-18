import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/api'))
from prooflane.bootstrap_storage import ensure_bucket

class S3Error(Exception):
    def __init__(self,code):
        self.response={'Error':{'Code':code}}

class FakeS3:
    def __init__(self,exists=True,versioning=True,policy=None):
        self.exists=exists;self.supports_versioning=versioning;self.status='Suspended';self.policy=policy;self.created=0;self.calls=[]
    def head_bucket(self,**kwargs):
        if not self.exists:raise S3Error('404')
    def create_bucket(self,**kwargs):self.exists=True;self.created+=1
    def put_bucket_versioning(self,**kwargs):
        self.calls.append(kwargs)
        if self.supports_versioning:self.status=kwargs['VersioningConfiguration']['Status']
    def get_bucket_versioning(self,**kwargs):return {'Status':self.status}
    def delete_bucket_policy(self,**kwargs):self.policy=None
    def get_bucket_policy(self,**kwargs):
        if self.policy is None:raise S3Error('NoSuchBucketPolicy')
        return {'Policy':self.policy}

class StorageBootstrap(unittest.TestCase):
    def test_new_bucket_private_and_versioned(self):
        client=FakeS3(exists=False)
        result=ensure_bucket(client,'dev-fixture-files')
        self.assertEqual(client.created,1)
        self.assertEqual(result['versioning'],'Enabled')
        self.assertEqual(result['anonymous_policy'],'absent')
    def test_repeated_bootstrap_does_not_recreate_bucket(self):
        client=FakeS3(exists=False)
        ensure_bucket(client,'bucket');ensure_bucket(client,'bucket')
        self.assertEqual(client.created,1)
    def test_access_denial_is_not_treated_as_missing_bucket(self):
        client=FakeS3()
        def forbidden(**kwargs):raise S3Error('403')
        client.head_bucket=forbidden
        with self.assertRaises(S3Error):ensure_bucket(client,'bucket')
        self.assertEqual(client.created,0)
    def test_versioning_failure_fails_closed(self):
        with self.assertRaises(RuntimeError):ensure_bucket(FakeS3(versioning=False),'bucket')
    def test_public_policy_removed(self):
        client=FakeS3(policy='public')
        ensure_bucket(client,'bucket');self.assertIsNone(client.policy)
    def test_unremoved_policy_is_not_accepted(self):
        client=FakeS3(policy='public');client.delete_bucket_policy=lambda **kwargs:None
        with self.assertRaises(RuntimeError):ensure_bucket(client,'bucket')
    def test_policy_lookup_permission_error_fails_closed(self):
        client=FakeS3()
        def forbidden(**kwargs):raise S3Error('AccessDenied')
        client.get_bucket_policy=forbidden
        with self.assertRaises(S3Error):ensure_bucket(client,'bucket')

if __name__=='__main__':unittest.main()
