"""S3/SQS notifications schedule work; they never approve or release content."""
import hashlib
import json
import logging
import time
from urllib.parse import unquote_plus


def notifications(body,bucket):
    if len(body)>1024*1024:raise ValueError('Notification exceeds bounds')
    data=json.loads(body)
    if data.get('Event')=='s3:TestEvent' and data.get('Bucket')==bucket:return []
    records=data.get('Records')
    if not isinstance(records,list) or not records or len(records)>1000:raise ValueError('Invalid notification envelope')
    result=[]
    for record in records:
        if record.get('eventSource')!='aws:s3' or not record.get('eventName','').startswith('ObjectCreated:'):
            raise ValueError('Unexpected storage event')
        s3=record.get('s3',{});obj=s3.get('object',{})
        if s3.get('bucket',{}).get('name')!=bucket:raise ValueError('Notification bucket mismatch')
        key=unquote_plus(obj.get('key',''));version=obj.get('versionId')
        if not key or not isinstance(version,str) or version in ('','null'):raise ValueError('Exact object version required')
        identity=[bucket,key,version,record['eventName'],obj.get('sequencer','')]
        result.append({'key':key,'object_version':version,'event_key':hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()})
    return result


def apply(db,record):
    from sqlalchemy import select
    from .db import Version,File,StorageReceipt,Event,now
    from .domain import policy,enqueue
    version=db.scalar(select(Version).where(Version.storage_key==record['key'],Version.object_version==record['object_version']))
    if not version:raise LookupError('Object metadata is not committed; retry notification')
    file=db.scalar(select(File).where(File.id==version.file_id,File.tenant_id==version.tenant_id).with_for_update())
    if not file:raise LookupError('Logical file metadata unavailable')
    if db.scalar(select(StorageReceipt.id).where(StorageReceipt.event_key==record['event_key'])):return 'duplicate'
    p=policy(db,version.tenant_id,True)
    # A worker/policy update could have committed while the file lock was pending.
    # Never write a generation copied from the earlier, unlocked lookup.
    db.refresh(version)
    if not file.deleted and version.status not in ('QUARANTINED','FAILED'):
        from .db import Scan
        scan=db.scalar(select(Scan).where(Scan.version_id==version.id,Scan.generation==version.generation).order_by(Scan.created.desc()))
        if version.status=='APPROVED' and (not scan or scan.epoch!=p.epoch or scan.expires<=now()):
            version.generation+=1;version.status='EVIDENCE_STALE'
        if version.status in ('PENDING','EVIDENCE_STALE'):enqueue(db,version,p)
    db.add(StorageReceipt(tenant_id=version.tenant_id,event_key=record['event_key'],version_id=version.id))
    db.add(Event(tenant_id=version.tenant_id,file_id=version.file_id,version_id=version.id,kind='STORAGE_EVENT_RECONCILED',details={'receipt':record['event_key']}))
    return 'recorded'


def run():
    import boto3
    from .config import settings
    from .db import SessionLocal
    s=settings()
    if not s.storage_event_queue_url:return
    queue=boto3.client('sqs',region_name=s.aws_region)
    while True:
        try:
            response=queue.receive_message(QueueUrl=s.storage_event_queue_url,WaitTimeSeconds=20,MaxNumberOfMessages=10,VisibilityTimeout=180)
            for message in response.get('Messages',[]):
                try:
                    records=notifications(message['Body'],s.s3_bucket)
                    with SessionLocal() as db:
                        for record in records:apply(db,record)
                        db.commit()
                    queue.delete_message(QueueUrl=s.storage_event_queue_url,ReceiptHandle=message['ReceiptHandle'])
                except Exception as error:
                    # Never print notification bodies, URLs with credentials, or keys.
                    logging.warning('Storage notification deferred: %s',type(error).__name__)
        except Exception as error:
            logging.warning('Storage event poll failed: %s',type(error).__name__)
            time.sleep(5)
