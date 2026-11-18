from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from urllib.parse import quote
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    environment: str = 'development'
    database_url: str = 'postgresql+psycopg://prooflane@localhost:5432/prooflane'
    database_host: str = ''
    database_user: str = 'prooflane'
    database_name: str = 'prooflane'
    database_password: str = ''
    database_sslmode: str = 'require'
    database_sslrootcert: str = ''
    redis_url: str = 'redis://localhost:6379/0'
    redis_host: str = ''
    redis_password: str = ''
    public_origin: str = 'http://localhost:5173'
    cookie_secure: bool = False
    storage_backend: str = 's3'
    local_storage: str = '.runtime/objects'
    s3_endpoint: str | None = 'http://localhost:9000'
    s3_bucket: str = 'dev-fixture-files'
    s3_access_key: str = ''
    s3_secret_key: str = ''
    aws_region: str = 'us-east-1'
    kms_key_id: str | None = None
    s3_bucket_key_enabled: bool = False
    clamav_host: str = 'localhost'
    clamav_port: int = 3310
    scanner_timeout: int = 60
    cnn_mode: Literal['disabled', 'mock'] = 'disabled'
    max_upload_bytes: int = 25 * 1024 * 1024
    evidence_ttl: int = 3600
    worker_capacity: int = 2
    tenant_capacity: int = 2
    max_attempts: int = 3
    lease_seconds: int = 180
    starvation_seconds: int = 120
    scheduler_fallback: str = 'edf'
    llm_provider: str = 'anthropic'
    anthropic_api_key: str = ''
    anthropic_model: str = ''
    model_directory: str = 'artifacts/models'
    storage_event_queue_url: str = ''
    research_results_path: str = 'artifacts/results-v2/results.json'

    @model_validator(mode='after')
    def cloud_connections(self):
        if self.database_host:
            from sqlalchemy import URL
            query={'sslmode':self.database_sslmode}
            if self.database_sslrootcert:query['sslrootcert']=self.database_sslrootcert
            self.database_url=URL.create('postgresql+psycopg',username=self.database_user,
                password=self.database_password,host=self.database_host,port=5432,
                database=self.database_name,query=query).render_as_string(hide_password=False)
        if self.redis_host:
            auth=':'+quote(self.redis_password,safe='')+'@' if self.redis_password else ''
            self.redis_url='rediss://'+auth+self.redis_host+':6379/0'
        if self.s3_endpoint=='':self.s3_endpoint=None
        return self

    def validate_runtime(self):
        if self.environment == 'production':
            if not self.cookie_secure or not self.public_origin.startswith('https://'):
                raise RuntimeError('Production requires HTTPS and secure cookies')
            if self.storage_backend != 's3' or not self.kms_key_id or self.s3_endpoint:
                raise RuntimeError('Production requires AWS S3 with KMS and the IAM credential chain')
            if not self.database_url.startswith('postgresql'):
                raise RuntimeError('Production requires PostgreSQL')

@lru_cache
def settings():
    s = Settings()
    s.validate_runtime()
    return s
