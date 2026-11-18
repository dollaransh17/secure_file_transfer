"""Persist scheduling-time facts instead of reconstructing mutable queue state."""
from sqlalchemy import select, func
from .db import Job, Version, Event, GraphEvent
from .config import settings
from ml.data import features, HORIZON
from ml.context import MAX_EVENTS, encode_event, snapshot

def job_features(db, job, at):
    version = db.get(Version, job.version_id)
    previous = db.scalar(select(Job.duration).where(
        Job.tenant_id == job.tenant_id, Job.file_id == job.file_id,
        Job.completed < at, Job.duration != None).order_by(Job.completed.desc())) or 0
    recent = db.scalar(select(func.count(Event.id)).where(
        Event.tenant_id == job.tenant_id, Event.file_id == job.file_id,
        Event.kind == 'DOWNLOAD_AUTHORIZED', Event.created < at,
        Event.created >= at - HORIZON)) or 0
    queued = db.scalar(select(func.count(Job.id)).where(
        Job.tenant_id == job.tenant_id, Job.status == 'PENDING', Job.created <= at)) or 0
    return features(version.size, at, job.created, job.deadline, previous,
                    recent, queued, job.attempts, settings().worker_capacity)

def graph_context(db, tenant, at):
    rows = list(db.scalars(select(GraphEvent).where(
        GraphEvent.tenant_id == tenant, GraphEvent.created < at)
        .order_by(GraphEvent.created.desc(), GraphEvent.id.desc()).limit(MAX_EVENTS)))
    return snapshot([encode_event(e.source, e.target, e.created, e.edge, e.features, e.id)
                     for e in rows], at)
