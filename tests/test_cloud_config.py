from urllib.parse import urlparse,unquote
import pytest
from sqlalchemy import make_url
from prooflane.config import Settings

def cloud_settings(**overrides):
    values=dict(environment='production',cookie_secure=True,storage_backend='s3',
        public_origin='https://files.example.test',database_host='rds.internal',
        database_password='special:/@#%value',database_sslmode='verify-full',database_sslrootcert='/etc/rds.pem',
        redis_host='cache.internal',redis_password='special:/@#%value',s3_endpoint='',kms_key_id='configured-kms-arn')
    values.update(overrides)
    return Settings(_env_file=None,**values)

def test_cloud_secrets_are_escaped_and_s3_uses_iam_chain(monkeypatch):
    # _env_file=None disables dotenv, not process environment. The API tests
    # intentionally set STORAGE_BACKEND=local; this cloud case must override it.
    monkeypatch.setenv('STORAGE_BACKEND','local')
    password='special:/@#%value'
    config=cloud_settings()
    config.validate_runtime()
    assert config.storage_backend=='s3'
    url=make_url(config.database_url)
    assert url.password==password
    assert url.query['sslmode']=='verify-full'
    assert url.query['sslrootcert']=='/etc/rds.pem'
    assert config.s3_endpoint is None
    redis=urlparse(config.redis_url)
    assert redis.scheme=='rediss'
    assert unquote(redis.password)==password

@pytest.mark.parametrize('overrides',[
    {'storage_backend':'local'},
    {'kms_key_id':None},
    {'s3_endpoint':'http://localhost:9000'},
])
def test_production_still_rejects_invalid_storage(overrides):
    with pytest.raises(RuntimeError,match='Production requires AWS S3'):
        cloud_settings(**overrides).validate_runtime()
