import hashlib
from sqlalchemy import select
from fastapi import HTTPException
from .db import *
from .config import settings
from .security import ReleaseFacts, release_denial
from .storage import storage

def event(db, user, kind, file=None, version=None, **details):
    db.add(Event(tenant_id=user.tenant_id, actor_id=user.id, kind=kind,
                 file_id=file.id if file else None, version_id=version.id if version else None, details=details))

def edge(db, tenant, source, target, kind, **features):
    db.add(GraphEvent(tenant_id=tenant, source=source, target=target, edge=kind, features=features))

def locked_file(db, user, file_id, owner=False):
    # ACL mutations and gateway decisions serialize on this same file row.
    f = db.scalar(select(File).where(File.id==file_id, File.tenant_id==user.tenant_id, File.deleted==False).with_for_update())
    if not f: raise HTTPException(404, 'File not found')
    permitted = f.owner_id == user.id or (not owner and db.scalar(select(Permission.id).where(
        Permission.file_id==f.id, Permission.user_id==user.id, Permission.tenant_id==user.tenant_id, Permission.active==True)))
    if not permitted:
        event(db,user,'ACCESS_DENIED',f)
        db.commit()
        raise HTTPException(403,'Access denied')
    return f

def policy(db, tenant, lock=False):
    q = select(Policy).where(Policy.tenant_id==tenant)
    return db.scalar(q.with_for_update() if lock else q)

def enqueue(db, version, p):
    key = f'{version.id}:{p.epoch}:{version.generation}:scan_integrity'
    old = db.scalar(select(Job).where(Job.idempotency_key==key))
    if old: return old
    j = Job(id=uid(), tenant_id=version.tenant_id,file_id=version.file_id,version_id=version.id,
            epoch=p.epoch,generation=version.generation,idempotency_key=key,deadline=now()+300,cost=max(1,version.size/1e6))
    db.add(j)
    edge(db,version.tenant_id,'job:'+j.id,'version:'+version.id,'JOB_VERIFIES_VERSION',size=version.size)
    return j

def release(db, user, file_id, version_id, *, purpose='download'):
    if purpose not in ('download', 'preview'):
        raise ValueError('Invalid release purpose')
    f = locked_file(db,user,file_id)
    if purpose == 'download' and f.owner_id != user.id and not db.scalar(select(Permission.id).where(
        Permission.file_id==f.id,Permission.user_id==user.id,Permission.tenant_id==user.tenant_id,
        Permission.active==True,Permission.can_download==True)):
        event(db,user,'DOWNLOAD_DENIED',f,reason='Shared access is view-only')
        db.commit()
        raise HTTPException(403,'View-only access: open this file in the reader. Ask the owner for download permission.')
    v = db.scalar(select(Version).where(Version.id==version_id,Version.file_id==f.id,Version.tenant_id==user.tenant_id))
    if not v: raise HTTPException(404,'Version not found')
    p = policy(db,user.tenant_id,True)
    scan = db.scalar(select(Scan).where(Scan.version_id==v.id,Scan.generation==v.generation).order_by(Scan.created.desc()))
    integ = db.scalar(select(Integrity).where(Integrity.version_id==v.id,Integrity.generation==v.generation).order_by(Integrity.created.desc()))
    facts = ReleaseFacts(True, f.current_version_id==v.id, v.status,
        bool(scan and scan.result=='CLEAN'), bool(scan and scan.digest==v.digest and scan.object_version==v.object_version),
        bool(scan and scan.epoch==p.epoch), bool(integ and integ.valid and integ.baseline_digest==v.digest and integ.observed_digest==v.digest),
        min(scan.expires,integ.expires) if scan and integ else 0)
    reason = release_denial(facts)
    if reason:
        event(db,user,'PREVIEW_HELD' if purpose == 'preview' else 'DOWNLOAD_HELD',f,v,reason=reason)
        db.commit()
        raise HTTPException(423,reason)
    # Rehash exact private object before any bytes leave. Lock retained until decision commit.
    data = storage().read(v.storage_key,v.object_version)
    if hashlib.sha256(data).hexdigest()!=v.digest:
        v.status='EVIDENCE_STALE'
        v.generation+=1
        enqueue(db,v,p)
        event(db,user,'INTEGRITY_MISMATCH',f,v)
        db.commit()
        raise HTTPException(423,'Integrity mismatch')
    # Object reads may take long enough for evidence to expire while locks are held.
    # Recheck at the decision boundary, after the byte read/hash.
    if min(scan.expires,integ.expires)<=now():
        event(db,user,'PREVIEW_HELD' if purpose == 'preview' else 'DOWNLOAD_HELD',f,v,reason='Security evidence expired during object verification')
        db.commit()
        raise HTTPException(423,'Security evidence expired')
    event(db,user,'PREVIEW_AUTHORIZED' if purpose == 'preview' else 'DOWNLOAD_AUTHORIZED',f,v)
    edge(db,user.tenant_id,'user:'+user.id,'version:'+v.id,'USER_REQUESTED_FILE',authorized=True,purpose=purpose)
    # Linearization point: commit while file and policy locks are held.
    db.commit()
    return f,v,data
