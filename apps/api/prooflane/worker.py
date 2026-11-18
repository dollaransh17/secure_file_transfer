"""Durable PostgreSQL job queue: leases, fencing tokens, SKIP LOCKED, retries.
Redis is used for rate limiting, never as the sole source of queued work.
"""
import hashlib
import time
import socket
from sqlalchemy import select, func
from .db import *
from .config import settings
from .domain import enqueue, policy, edge
from .storage import storage
from . import scanner
from .scheduling import Candidate, rank

TERMINAL=('COMPLETE','DEAD','SUPERSEDED')
def reconcile(db):
    # Singleton scheduling/reconciliation lock across workers. PostgreSQL only.
    if db.bind.dialect.name=='postgresql': db.execute(select(func.pg_advisory_xact_lock(77125)))
    at=now()
    # Same lock order as release, policy updates and worker completion.
    list(db.scalars(select(File).order_by(File.id).with_for_update()))
    for j in db.scalars(select(Job).where(Job.status=='RUNNING',Job.lease_until<at).with_for_update()):
        j.status='DEAD' if j.attempts>=settings().max_attempts else 'PENDING'
        j.worker=None; j.lease_token=None; j.available=at+2**j.attempts
        v=db.get(Version,j.version_id)
        if v.generation==j.generation:
            v.status='FAILED' if j.status=='DEAD' else 'PENDING'
    for v in db.scalars(select(Version).where(Version.status.in_(['APPROVED','PENDING','EVIDENCE_STALE']))):
        p=policy(db,v.tenant_id)
        latest=db.scalar(select(Scan).where(Scan.version_id==v.id,Scan.generation==v.generation).order_by(Scan.created.desc()))
        if v.status=='APPROVED' and (not latest or latest.expires<=at or latest.epoch!=p.epoch):
            v.status='EVIDENCE_STALE'; v.generation+=1
            reason='EVIDENCE_MISSING' if not latest else 'POLICY_INVALIDATED' if latest.epoch!=p.epoch else 'EVIDENCE_EXPIRED'
            db.add(Event(tenant_id=v.tenant_id,file_id=v.file_id,version_id=v.id,kind=reason,details={'epoch':p.epoch}))
        if v.status in ('PENDING','EVIDENCE_STALE'): enqueue(db,v,p)
    db.commit()

def claim(db, worker):
    scheduling_started=time.perf_counter()
    if db.bind.dialect.name=='postgresql': db.execute(select(func.pg_advisory_xact_lock(77125)))
    running=list(db.scalars(select(Job).where(Job.status=='RUNNING')))
    if len(running)>=settings().worker_capacity: db.rollback(); return None
    at=now()
    jobs=list(db.scalars(select(Job).where(Job.status=='PENDING',Job.available<=at,Job.attempts<settings().max_attempts).with_for_update(skip_locked=True).limit(1000)))
    eligible=[j for j in jobs if sum(r.tenant_id==j.tenant_id for r in running)<settings().tenant_capacity]
    # Global oldest/deadline selection across tenants, then each tenant's configured strategy.
    tenants={j.tenant_id for j in eligible}
    selections=[]
    records={}
    for tenant in tenants:
        subset=[j for j in eligible if j.tenant_id==tenant]
        strategy=db.get(Tenant,tenant).strategy
        predictions={}; fallback=None; version=None
        if strategy in ('lightgbm','tgn'):
            try:
                from .predict import predict_jobs
                predictions,version=predict_jobs(db,subset,strategy,at)
            except (FileNotFoundError,ImportError,ValueError,RuntimeError) as exc:
                fallback=type(exc).__name__; strategy=settings().scheduler_fallback
        ranked=rank([Candidate(j.id,j.tenant_id,j.created,j.deadline,j.cost,j.attempts) for j in subset],strategy,at,predictions,settings().starvation_seconds)
        if ranked:
            selections.append(ranked[0]); records[ranked[0].id]=(strategy,predictions.get(ranked[0].id),fallback,version)
    if not selections: db.rollback(); return None
    winner=rank(selections,'edf',at,starvation=settings().starvation_seconds)[0]
    job=next(j for j in eligible if j.id==winner.id)
    strategy,prediction,fallback,version=records[job.id]
    from .features import job_features,graph_context
    recorded_features=job_features(db,job,at)
    recorded_context=graph_context(db,job.tenant_id,at)
    job.status='RUNNING'; job.worker=worker; job.attempts+=1
    v=db.get(Version,job.version_id)
    if v.generation==job.generation and v.status in ('PENDING','EVIDENCE_STALE'):
        v.status='VERIFYING'
    job.lease_token=uid(); job.lease_until=at+settings().lease_seconds; job.started=at
    db.add(Decision(tenant_id=job.tenant_id,job_id=job.id,strategy=strategy,created=at,inputs=dict(
        feature_schema=2,features=recorded_features,context=recorded_context,attempt=job.attempts,scheduler_seconds=time.perf_counter()-scheduling_started,
        cost=job.cost,deadline=job.deadline,age=at-job.created,prediction=prediction,model_version=version,fallback=fallback,
        constraints=['mandatory verification','capacity','tenant capacity','deadline urgency','starvation','retry limit'])))
    db.add(VerificationEvent(tenant_id=job.tenant_id,job_id=job.id,kind='CLAIMED'))
    db.commit()
    return job.id,job.lease_token

def process(job_id, token, scan_fn=None):
    scan_fn=scan_fn or scanner.scan
    with SessionLocal() as db:
        j=db.get(Job,job_id); v=db.get(Version,j.version_id)
        key,object_version,digest=v.storage_key,v.object_version,v.digest
    start=time.monotonic()
    try:
        data=storage().read(key,object_version)
        observed=hashlib.sha256(data).hexdigest()
        verdict=scan_fn(data)
        error=None
    except Exception as exc:
        verdict=None; observed=''; error=type(exc).__name__
    with SessionLocal() as db:
        # Lock file then policy to match gateway lock ordering.
        j=db.get(Job,job_id)
        db.scalar(select(File).where(File.id==j.file_id).with_for_update())
        p=policy(db,j.tenant_id,True)
        j=db.scalar(select(Job).where(Job.id==job_id).with_for_update().execution_options(populate_existing=True))
        if j.status!='RUNNING' or j.lease_token!=token or j.lease_until<=now(): return False
        v=db.get(Version,j.version_id)
        if j.epoch!=p.epoch or j.generation!=v.generation:
            j.status='SUPERSEDED'; j.completed=now(); db.commit(); return False
        if error:
            j.error=error; j.status='DEAD' if j.attempts>=settings().max_attempts else 'PENDING'
            j.available=now()+2**j.attempts; j.lease_token=None
            v.status='FAILED' if j.status=='DEAD' else 'PENDING'
            db.add(Event(tenant_id=j.tenant_id,file_id=j.file_id,version_id=v.id,kind='SCANNER_ERROR',details={'error':error}))
        else:
            expires=now()+p.ttl
            s=Scan(id=uid(),tenant_id=j.tenant_id,version_id=v.id,digest=digest,object_version=object_version,
                   epoch=j.epoch,generation=j.generation,result=verdict.result,engine=verdict.engine,
                   duration=verdict.duration,expires=expires)
            i=Integrity(id=uid(),tenant_id=j.tenant_id,version_id=v.id,baseline_digest=digest,observed_digest=observed,
                        valid=observed==digest,generation=j.generation,expires=expires)
            db.add_all([s,i])
            v.status='APPROVED' if verdict.result=='CLEAN' and observed==digest else 'QUARANTINED'
            j.status='COMPLETE';j.completed=now();j.duration=time.monotonic()-start
            edge(db,j.tenant_id,'version:'+v.id,'scan:'+s.id,'VERSION_HAS_SCAN',result=verdict.result)
            edge(db,j.tenant_id,'version:'+v.id,'integrity:'+i.id,'VERSION_HAS_INTEGRITY',valid=i.valid)
            edge(db,j.tenant_id,'policy:'+p.id,'scan:'+s.id,'POLICY_GOVERNS_SCAN',epoch=p.epoch)
            db.add(Event(tenant_id=j.tenant_id,file_id=j.file_id,version_id=v.id,kind='VERIFICATION_'+v.status,details={'job_id':j.id,'epoch':j.epoch}))
            if settings().cnn_mode == 'mock':
                from .cnn_demo import record
                record(db,v)
        db.add(VerificationEvent(tenant_id=j.tenant_id,job_id=j.id,kind=j.status))
        db.commit()
        return True

def main():
    if settings().storage_event_queue_url:
        from threading import Thread
        from .storage_events import run
        Thread(target=run,name='storage-events',daemon=True).start()
    worker=socket.gethostname()+'-'+uid()[:8]
    while True:
        try:
            with SessionLocal() as db: reconcile(db); chosen=claim(db,worker)
            if chosen: process(*chosen)
            else: time.sleep(1)
        except Exception:
            import logging
            logging.exception('Worker cycle failed')
            time.sleep(3)
if __name__=='__main__': main()
