import time
import uuid
from sqlalchemy import create_engine, String, Integer, Float, Boolean, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

def uid(): return str(uuid.uuid4())
def now(): return time.time()
class Base(DeclarativeBase): pass
class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
class Scoped(Identity):
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'), index=True)
class Tenant(Identity, Base):
    __tablename__ = 'tenants'
    name: Mapped[str] = mapped_column(String(120))
    strategy: Mapped[str] = mapped_column(String(20), default='edf')
class User(Scoped, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='member')
class Session(Identity, Base):
    __tablename__ = 'sessions'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(128))
    expires: Mapped[float] = mapped_column(Float)
    absolute_expires: Mapped[float] = mapped_column(Float)
class File(Scoped, Base):
    __tablename__ = 'files'
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(255))
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=now)
class Version(Scoped, Base):
    __tablename__ = 'file_versions'
    file_id: Mapped[str] = mapped_column(ForeignKey('files.id'), index=True)
    number: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    object_version: Mapped[str] = mapped_column(String(255))
    digest: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default='PENDING')
    generation: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[float] = mapped_column(Float, default=now)
    __table_args__ = (UniqueConstraint('file_id','number'),)
class Permission(Scoped, Base):
    __tablename__ = 'file_permissions'
    file_id: Mapped[str] = mapped_column(ForeignKey('files.id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    can_download: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    __table_args__ = (UniqueConstraint('file_id','user_id'),)
class Policy(Scoped, Base):
    __tablename__ = 'security_policies'
    epoch: Mapped[int] = mapped_column(Integer, default=1)
    ttl: Mapped[int] = mapped_column(Integer, default=3600)
    __table_args__ = (UniqueConstraint('tenant_id'),)
class PolicyEpoch(Scoped, Base):
    __tablename__ = 'policy_epochs'
    epoch: Mapped[int] = mapped_column(Integer)
    created: Mapped[float] = mapped_column(Float, default=now)
class Scan(Scoped, Base):
    __tablename__ = 'scan_evidence'
    version_id: Mapped[str] = mapped_column(ForeignKey('file_versions.id'), index=True)
    digest: Mapped[str] = mapped_column(String(64))
    object_version: Mapped[str] = mapped_column(String(255))
    epoch: Mapped[int] = mapped_column(Integer)
    generation: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(30))
    engine: Mapped[str] = mapped_column(String(255))
    duration: Mapped[float] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float, default=now)
    expires: Mapped[float] = mapped_column(Float)
class Integrity(Scoped, Base):
    __tablename__ = 'integrity_evidence'
    version_id: Mapped[str] = mapped_column(ForeignKey('file_versions.id'), index=True)
    baseline_digest: Mapped[str] = mapped_column(String(64))
    observed_digest: Mapped[str] = mapped_column(String(64))
    generation: Mapped[int] = mapped_column(Integer)
    valid: Mapped[bool] = mapped_column(Boolean)
    created: Mapped[float] = mapped_column(Float, default=now)
    expires: Mapped[float] = mapped_column(Float)
class Job(Scoped, Base):
    __tablename__ = 'verification_jobs'
    file_id: Mapped[str] = mapped_column(ForeignKey('files.id'))
    version_id: Mapped[str] = mapped_column(ForeignKey('file_versions.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30), default='scan_integrity')
    epoch: Mapped[int] = mapped_column(Integer)
    generation: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='PENDING', index=True)
    created: Mapped[float] = mapped_column(Float, default=now)
    deadline: Mapped[float] = mapped_column(Float)
    available: Mapped[float] = mapped_column(Float, default=now)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=1)
    worker: Mapped[str | None] = mapped_column(String(100))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[float | None] = mapped_column(Float)
    started: Mapped[float | None] = mapped_column(Float)
    completed: Mapped[float | None] = mapped_column(Float)
    duration: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(String(255))
class Event(Scoped, Base):
    __tablename__ = 'audit_events'
    actor_id: Mapped[str | None] = mapped_column(String(36))
    file_id: Mapped[str | None] = mapped_column(String(36), index=True)
    version_id: Mapped[str | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(60), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=now, index=True)
class VerificationEvent(Scoped, Base):
    __tablename__ = 'verification_events'
    job_id: Mapped[str] = mapped_column(ForeignKey('verification_jobs.id'))
    kind: Mapped[str] = mapped_column(String(60))
    created: Mapped[float] = mapped_column(Float, default=now)
class GraphEvent(Scoped, Base):
    __tablename__ = 'graph_events'
    source: Mapped[str] = mapped_column(String(100), index=True)
    target: Mapped[str] = mapped_column(String(100), index=True)
    edge: Mapped[str] = mapped_column(String(60))
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=now, index=True)
class Decision(Scoped, Base):
    __tablename__ = 'scheduler_decisions'
    job_id: Mapped[str] = mapped_column(ForeignKey('verification_jobs.id'))
    strategy: Mapped[str] = mapped_column(String(30))
    inputs: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=now)
class Model(Identity, Base):
    __tablename__ = 'model_registry'
    name: Mapped[str] = mapped_column(String(30))
    checkpoint: Mapped[str] = mapped_column(String(255))
    metrics: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=now)
class Experiment(Scoped, Base):
    __tablename__ = 'experiment_runs'
    config: Mapped[dict] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=now)
class Metric(Identity, Base):
    __tablename__ = 'experiment_metrics'
    run_id: Mapped[str] = mapped_column(ForeignKey('experiment_runs.id'))
    name: Mapped[str] = mapped_column(String(80))
    value: Mapped[float] = mapped_column(Float)
class AssistantQuery(Scoped, Base):
    __tablename__ = 'assistant_queries'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    event_ids: Mapped[list] = mapped_column(JSON)
    usage: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(60))
    created: Mapped[float] = mapped_column(Float, default=now)

class StorageReceipt(Scoped, Base):
    __tablename__ = 'storage_event_receipts'
    event_key: Mapped[str] = mapped_column(String(64), unique=True)
    version_id: Mapped[str] = mapped_column(ForeignKey('file_versions.id'))
    created: Mapped[float] = mapped_column(Float, default=now)

Index('job_claim', Job.status, Job.available, Job.deadline)
engine = create_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
def database():
    with SessionLocal() as db:
        yield db
