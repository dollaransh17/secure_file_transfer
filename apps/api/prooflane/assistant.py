import re
from rank_bm25 import BM25Okapi
from sqlalchemy import select, or_
from .db import *
from .config import settings
from .assistant_evidence import explain

# Only controlled event fields leave the process; names and metadata are excluded.
def retrieve(db,user,question):
    permitted=select(Permission.file_id).where(Permission.user_id==user.id,Permission.tenant_id==user.tenant_id,Permission.active==True)
    files=select(File.id).where(File.tenant_id==user.tenant_id,File.deleted==False,or_(File.owner_id==user.id,File.id.in_(permitted)))
    records=list(db.scalars(select(Event).where(Event.tenant_id==user.tenant_id,Event.file_id.in_(files),Event.kind!='MOCK_CNN_ANALYSIS').order_by(Event.created.desc()).limit(300)))
    if not records: return []
    corpus=[re.findall(r'\w+',(e.kind.replace('_',' ')+' '+str(e.version_id or '')).lower()) for e in records]
    scores=BM25Okapi(corpus).get_scores(re.findall(r'\w+',question.lower()))
    ranked=sorted(zip(scores,records),key=lambda pair:pair[0],reverse=True)[:12]
    safe_reasons={'Access denied','Version is not the current authorized target','Version has not been approved',
        'Exact-version scan evidence required','Scanner policy changed','Integrity verification required','Security evidence expired',
        'Security evidence expired during object verification'}
    result=[]
    for _,e in ranked:
        item=dict(id=e.id,kind=e.kind,version=e.version_id,timestamp=e.created)
        details=e.details if isinstance(e.details,dict) else {}
        if isinstance(details.get('reason'),str) and details['reason'] in safe_reasons:item['reason']=details['reason']
        if isinstance(details.get('epoch'),int):item['policy_epoch']=details['epoch']
        if isinstance(details.get('error'),str) and details['error'] in {'TimeoutError','ConnectionRefusedError','ConnectionResetError','RuntimeError','EndpointConnectionError'}:
            item['error_type']=details['error']
        job_id=details.get('job_id')
        if isinstance(job_id,str):
            job=db.scalar(select(Job).where(Job.id==job_id,Job.tenant_id==user.tenant_id,Job.file_id==e.file_id,Job.version_id==e.version_id))
            if job:
                decision=db.scalar(select(Decision).where(Decision.job_id==job.id,Decision.tenant_id==user.tenant_id,Decision.created<=e.created).order_by(Decision.created.desc()))
                if decision and decision.strategy in ('fifo','edf','rule','lightgbm','tgn'):
                    data=decision.inputs if isinstance(decision.inputs,dict) else {}
                    allowed={'mandatory verification','capacity','tenant capacity','deadline urgency','starvation','retry limit'}
                    item['scheduling']={'decision_id':decision.id,'method':decision.strategy,
                        'constraints':[v for v in (data.get('constraints') if isinstance(data.get('constraints'),list) else []) if isinstance(v,str) and v in allowed]}
        result.append(item)
    return result

def answer(db,user,question):
    evidence=retrieve(db,user,question)
    s=settings(); usage={}; status='evidence_only'
    configured=bool(s.anthropic_api_key and s.anthropic_model)
    text=('Claude is unavailable. Authorized recorded events are listed below.' if configured else
          'Claude is not configured. Authorized recorded events are listed below.') if evidence else 'No authorized event records match this request.'
    if evidence and s.anthropic_api_key and s.anthropic_model:
        try:
            from anthropic import Anthropic
            client=Anthropic(api_key=s.anthropic_api_key,timeout=20,max_retries=1)
            # Validate the configured model directly against this account.
            # No model ID is hardcoded and no SDK-specific pagination is required.
            client.models.retrieve(s.anthropic_model)
            text=explain(client,s.anthropic_model,question,evidence,usage);status='answered'
        except Exception as exc: status='unavailable:'+type(exc).__name__
    # Recheck authorization after network latency before exposing an answer.
    current_ids={e['id'] for e in retrieve(db,user,question)}
    if not {e['id'] for e in evidence}.issubset(current_ids):
        evidence=[];text='Access or evidence changed. Please ask again.';status='authorization_changed'
    db.add(AssistantQuery(tenant_id=user.tenant_id,user_id=user.id,event_ids=[e['id'] for e in evidence],usage=usage,status=status));db.commit()
    return {'answer':text,'events':evidence,'usage':usage,'status':status}
