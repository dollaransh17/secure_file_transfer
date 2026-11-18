"""Initialize only the private local bucket; never import database or ML modules."""
import json
import time


def error_code(error):
    return str(getattr(error, 'response', {}).get('Error', {}).get('Code', ''))


def ensure_bucket(client, bucket):
    """Idempotent local bootstrap. No success unless required policy is observable."""
    try:
        client.head_bucket(Bucket=bucket)
    except Exception as error:
        if error_code(error) not in ('404', 'NoSuchBucket', 'NotFound'):
            raise
        client.create_bucket(Bucket=bucket)
    client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={'Status': 'Enabled'})
    if client.get_bucket_versioning(Bucket=bucket).get('Status') != 'Enabled':
        raise RuntimeError('Bucket versioning was not enabled')
    # The application bucket must not carry an anonymous/public bucket policy.
    client.delete_bucket_policy(Bucket=bucket)
    try:
        client.get_bucket_policy(Bucket=bucket)
    except Exception as error:
        if error_code(error) not in ('NoSuchBucketPolicy', '404', 'NotFound'):
            raise
    else:
        raise RuntimeError('Bucket policy remains after private-storage bootstrap')
    return {'bucket': bucket, 'versioning': 'Enabled', 'anonymous_policy': 'absent'}


def main():
    import boto3
    from botocore.config import Config
    from botocore.exceptions import EndpointConnectionError, ConnectionClosedError, ConnectTimeoutError, ReadTimeoutError, ClientError
    from .config import settings
    s = settings()
    if s.environment != 'development' or not s.s3_endpoint or s.storage_backend != 's3':
        raise RuntimeError('Automatic bucket bootstrap is only for explicit development S3 endpoints')
    client = boto3.client('s3', endpoint_url=s.s3_endpoint, region_name=s.aws_region,
        aws_access_key_id=s.s3_access_key, aws_secret_access_key=s.s3_secret_key,
        config=Config(connect_timeout=3, read_timeout=5, retries={'max_attempts': 1}))
    end = time.monotonic() + 120
    while True:
        try:
            result = ensure_bucket(client, s.s3_bucket)
            print(json.dumps(result))
            return
        except (EndpointConnectionError, ConnectionClosedError, ConnectTimeoutError, ReadTimeoutError):
            if time.monotonic() >= end:
                raise RuntimeError('Local object store did not become reachable within 120 seconds') from None
        except ClientError as error:
            if error_code(error) not in ('500', '503', 'ServiceUnavailable', 'XMinioServerNotInitialized'):
                raise
            if time.monotonic() >= end:
                raise RuntimeError('Local object store did not become ready within 120 seconds') from None
        time.sleep(2)


if __name__ == '__main__':
    main()
