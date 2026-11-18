"""Explicit local endpoint credentials; real AWS always uses the SDK chain."""


def client_options(config):
    options = {'endpoint_url': config.s3_endpoint, 'region_name': config.aws_region}
    if config.s3_endpoint and config.environment != 'production':
        options.update(aws_access_key_id=config.s3_access_key,
                       aws_secret_access_key=config.s3_secret_key)
    return options


def encryption_options(config):
    if not config.kms_key_id:
        return {}
    options = {'ServerSideEncryption': 'aws:kms'}
    # Let S3 select/create its AWS-managed key on a new account's first write.
    # Explicit customer-managed identifiers must still be sent unchanged.
    if config.kms_key_id != 'alias/aws/s3':
        options['SSEKMSKeyId'] = config.kms_key_id
    if config.s3_bucket_key_enabled:
        options['BucketKeyEnabled'] = True
    return options
