"""Private, immutable storage. No browser receives object-store credentials or URLs."""
import hashlib
from pathlib import Path
from functools import lru_cache
import boto3
from .config import settings
from .db import uid
from .storage_options import client_options, encryption_options

class LocalStorage:
    """Explicit development/test adapter. Never selected on S3 errors."""
    def __init__(self):
        self.root = Path(settings().local_storage).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
    def put(self, key, stream):
        version = uid()
        path = self.root / (hashlib.sha256(key.encode()).hexdigest() + '-' + version)
        with path.open('xb') as out:
            while chunk := stream.read(65536): out.write(chunk)
        path.chmod(0o600)
        return version
    def read(self, key, version):
        with (self.root / (hashlib.sha256(key.encode()).hexdigest() + '-' + version)).open('rb') as stream:
            return stream.read(settings().max_upload_bytes + 1)

class S3Storage:
    def __init__(self):
        s = settings()
        self.client = boto3.client('s3', **client_options(s))
        self.bucket = s.s3_bucket
    def put(self, key, stream):
        if self.client.get_bucket_versioning(Bucket=self.bucket).get('Status') != 'Enabled':
            raise RuntimeError('Bucket versioning must be enabled')
        encryption = encryption_options(settings())
        r = self.client.put_object(Bucket=self.bucket, Key=key, Body=stream, **encryption)
        version = r.get('VersionId')
        if not version or version == 'null': raise RuntimeError('Immutable version unavailable')
        return version
    def read(self, key, version):
        body = self.client.get_object(Bucket=self.bucket, Key=key, VersionId=version)['Body']
        try: return body.read(settings().max_upload_bytes + 1)
        finally: body.close()

@lru_cache
def storage():
    return LocalStorage() if settings().storage_backend == 'local' else S3Storage()
