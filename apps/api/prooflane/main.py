import csv
import io
import json
import hashlib
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import quote
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Request, Response, File as Upload
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError
from redis import Redis
from .db import *
from .auth import current, researcher, issue, hasher, DUMMY, VerificationError, InvalidHashError
from .domain import locked_file, event, edge, enqueue, policy, release
from .config import settings
from .storage import storage
from .assistant import answer

app=FastAPI(title='Prooflane',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=[settings().public_origin],allow_credentials=True,allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Content-Type','X-CSRF-Token'])

@app.middleware('http')
async def protections(request,call_next):
    if request.url.path.startswith('/api'):
        try:
            redis=Redis.from_url(settings().redis_url,socket_connect_timeout=1,socket_timeout=1)
            key='rate:'+hashlib.sha256((request.client.host+':'+str(int(now()//60))).encode()).hexdigest()
            # Atomic expiry, including first request.
            count=redis.eval("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],61) end; return n",1,key)
            if count>180: return Response('Rate limit exceeded',429)
        except Exception:
            if settings().environment=='production': return Response('Rate limiter unavailable',503)
    r=await call_next(request)
    r.headers['X-Content-Type-Options']='nosniff'
    r.headers['Referrer-Policy']='no-referrer'
    r.headers['Cache-Control']='no-store'
    r.headers['X-Frame-Options']='DENY'
    return r

class Credentials(BaseModel):
    email: str = Field(min_length=3,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=12,max_length=128)
class Rename(BaseModel):
    name: str=Field(min_length=1,max_length=200,pattern=r'^[^/\\\x00-\x1f]+$')
class Share(BaseModel):
    email: str
    can_download: bool = False
class Question(BaseModel):
    question: str=Field(min_length=1,max_length=2000)
class Strategy(BaseModel):
    strategy: str=Field(pattern='^(fifo|edf|rule|lightgbm|tgn)$')

def public_user(u): return dict(id=u.id,email=u.email,role=u.role,tenant_id=u.tenant_id)
def serialize(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns}
def authorized_files(user):
    ids=select(Permission.file_id).where(Permission.user_id==user.id,Permission.tenant_id==user.tenant_id,Permission.active==True)
    return select(File).where(File.tenant_id==user.tenant_id,File.deleted==False,or_(File.owner_id==user.id,File.id.in_(ids)))

@app.get('/api/health')
def health(db=Depends(database)):
    db.execute(select(1)); return {'status':'ok','database':db.bind.dialect.name}
@app.post('/api/auth/register')
def register(body:Credentials,response:Response,request:Request,db=Depends(database)):
    if request.headers.get('origin')!=settings().public_origin: raise HTTPException(403,'Origin rejected')
    # Registration creates an isolated workspace. Invitations are explicit, same-tenant only.
    t=Tenant(id=uid(),name='Research workspace');db.add(t);db.flush()
    u=User(id=uid(),tenant_id=t.id,email=body.email.lower(),password_hash=hasher.hash(body.password),role='researcher')
    db.add_all([u,Policy(tenant_id=t.id,ttl=settings().evidence_ttl)])
    try: db.flush()
    except IntegrityError: db.rollback();raise HTTPException(409,'Registration unavailable for this email')
    csrf=issue(db,u,response);db.commit();return {'user':public_user(u),'csrf':csrf}
@app.post('/api/auth/login')
def login(body:Credentials,response:Response,request:Request,db=Depends(database)):
    if request.headers.get('origin')!=settings().public_origin: raise HTTPException(403,'Origin rejected')
    u=db.scalar(select(User).where(User.email==body.email.lower()))
    try: hasher.verify(u.password_hash if u else DUMMY,body.password)
    except (VerificationError,InvalidHashError): raise HTTPException(401,'Invalid email or password')
    if not u: raise HTTPException(401,'Invalid email or password')
    csrf=issue(db,u,response);db.commit();return {'user':public_user(u),'csrf':csrf}
@app.get('/api/auth/me')
def me(request:Request,user=Depends(current)):
    return {'user':public_user(user),'csrf':request.state.auth_session.csrf}
@app.post('/api/auth/refresh')
def refresh(request:Request,response:Response,user=Depends(current),db=Depends(database)):
    old=db.get(Session,request.state.auth_session.id)
    absolute=old.absolute_expires;db.delete(old)
    csrf=issue(db,user,response,absolute);db.commit();return {'user':public_user(user),'csrf':csrf}
@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user=Depends(current),db=Depends(database)):
    db.delete(db.get(Session,request.state.auth_session.id));db.commit();response.delete_cookie('prooflane_session');return {'ok':True}
@app.post('/api/workspace/members')
def add_member(body:Credentials,user=Depends(researcher),db=Depends(database)):
    u=User(tenant_id=user.tenant_id,email=body.email.lower(),password_hash=hasher.hash(body.password),role='member');db.add(u)
    try: db.commit()
    except IntegrityError: db.rollback();raise HTTPException(409,'Email unavailable')
    return public_user(u)
@app.get('/api/workspace/members')
def members(user=Depends(current),db=Depends(database)):
    return [public_user(u) for u in db.scalars(select(User).where(User.tenant_id==user.tenant_id))]

@app.get('/api/files')
def files(user=Depends(current),db=Depends(database)):
    result=[]
    for f in db.scalars(authorized_files(user).order_by(File.created.desc())):
        v=db.get(Version,f.current_version_id)
        result.append(dict(**serialize(f),version=serialize(v) if v else None,shared=bool(db.scalar(select(Permission.id).where(Permission.file_id==f.id,Permission.active==True))),owned=f.owner_id==user.id))
    return result
@app.get('/api/dashboard')
def dashboard(user=Depends(current),db=Depends(database)):
    rows=files(user,db)
    return dict(total=len(rows),storage=sum(f['version']['size'] for f in rows if f['version']),
                approved=sum(f['version']['status']=='APPROVED' for f in rows if f['version']),
                pending=sum(f['version']['status'] in ('PENDING','VERIFYING','EVIDENCE_STALE') for f in rows if f['version']),
                quarantined=sum(f['version']['status']=='QUARANTINED' for f in rows if f['version']),shared=sum(f['shared'] for f in rows),events=events(user,db))

def inspect_type(name,data):
    ext=Path(name).suffix.lower()
    allowed={'.txt':'text/plain','.csv':'text/csv','.json':'application/json','.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}
    if ext not in allowed: raise HTTPException(415,'Supported formats: TXT, CSV, JSON, PDF, PNG, JPEG')
    if ext=='.pdf' and not data.startswith(b'%PDF-'): raise HTTPException(415,'PDF signature invalid')
    if ext=='.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'): raise HTTPException(415,'PNG signature invalid')
    if ext in ('.jpg','.jpeg') and not data.startswith(b'\xff\xd8\xff'): raise HTTPException(415,'JPEG signature invalid')
    if ext in ('.txt','.csv','.json'):
        try: text=data.decode('utf-8')
        except UnicodeError: raise HTTPException(415,'Text must be UTF-8')
        if '\0' in text: raise HTTPException(415,'Binary content in text file')
        if ext=='.json':
            try: json.loads(text)
            except ValueError: raise HTTPException(415,'Invalid JSON')
    return allowed[ext]

@app.post('/api/files')
def upload(file:UploadFile=Upload(...),file_id:str|None=None,user=Depends(current),db=Depends(database)):
    name=Path(file.filename or 'untitled.txt').name
    Rename(name=name)
    # Spool to bounded private quarantine, hash while streaming.
    size=0;digest=hashlib.sha256()
    with tempfile.TemporaryFile() as stream:
        while chunk:=file.file.read(65536):
            size+=len(chunk)
            if size>settings().max_upload_bytes: raise HTTPException(413,'File exceeds upload limit')
            digest.update(chunk);stream.write(chunk)
        stream.seek(0);mime=inspect_type(name,stream.read());stream.seek(0)
        if file_id: f=locked_file(db,user,file_id,True)
        else:
            f=File(id=uid(),tenant_id=user.tenant_id,owner_id=user.id,name=name);db.add(f);db.flush()
        number=(db.scalar(select(func.max(Version.number)).where(Version.file_id==f.id)) or 0)+1
        version_id=uid();key=f'{user.tenant_id}/{f.id}/{version_id}'
        object_version=storage().put(key,stream)
    v=Version(id=version_id,tenant_id=user.tenant_id,file_id=f.id,number=number,storage_key=key,object_version=object_version,digest=digest.hexdigest(),size=size,mime=mime,status='PENDING',generation=0)
    db.add(v);db.flush();f.current_version_id=v.id
    enqueue(db,v,policy(db,user.tenant_id));event(db,user,'UPLOAD_QUARANTINED',f,v,size=size)
    edge(db,user.tenant_id,'user:'+user.id,'file:'+f.id,'USER_UPLOADED_FILE')
    edge(db,user.tenant_id,'file:'+f.id,'version:'+v.id,'FILE_HAS_VERSION',size=size)
    db.commit();return serialize(v)
@app.get('/api/files/{file_id}')
def detail(file_id:str,user=Depends(current),db=Depends(database)):
    f=locked_file(db,user,file_id)
    versions=list(db.scalars(select(Version).where(Version.file_id==f.id).order_by(Version.number.desc())))
    ids=[v.id for v in versions]
    result=dict(file=serialize(f),versions=[serialize(v) for v in versions],scans=[serialize(s) for s in db.scalars(select(Scan).where(Scan.version_id.in_(ids)))],integrity=[serialize(i) for i in db.scalars(select(Integrity).where(Integrity.version_id.in_(ids)))],permissions=[serialize(p) for p in db.scalars(select(Permission).where(Permission.file_id==f.id))],events=[serialize(e) for e in db.scalars(select(Event).where(Event.file_id==f.id).order_by(Event.created.desc()).limit(100))])
    current_version = next((v for v in versions if v.id == f.current_version_id), None)
    demo = db.scalar(select(Event).where(Event.file_id==f.id, Event.tenant_id==user.tenant_id,
        Event.version_id==f.current_version_id, Event.kind=='MOCK_CNN_ANALYSIS').order_by(Event.created.desc()))
    result['cnn_demo'] = {'enabled': settings().cnn_mode == 'mock', 'result':
        demo.details if demo and current_version and demo.details.get('generation')==current_version.generation
        and demo.details.get('digest')==current_version.digest else None}
    if f.owner_id == user.id:
        s = settings()
        result['storage_location'] = {'backend': s.storage_backend,
            'bucket': s.s3_bucket if s.storage_backend == 's3' else None,
            'region': s.aws_region if s.storage_backend == 's3' else None,
            'aws_console': s.storage_backend == 's3' and not s.s3_endpoint}
    db.commit();return result

@app.post('/api/files/{file_id}/cnn-demo')
def run_cnn_demo(file_id:str,user=Depends(current),db=Depends(database)):
    if settings().cnn_mode != 'mock': raise HTTPException(409,'Mock CNN demo is disabled')
    f=locked_file(db,user,file_id,True)
    v=db.get(Version,f.current_version_id)
    if not v: raise HTTPException(409,'No current file version')
    from .cnn_demo import record
    record(db,v)
    db.commit();return {'ok':True,'mode':'mock','release_authority':False}
@app.patch('/api/files/{file_id}')
def rename(file_id:str,body:Rename,user=Depends(current),db=Depends(database)):
    f=locked_file(db,user,file_id,True);f.name=body.name;event(db,user,'FILE_RENAMED',f);db.commit();return {'ok':True}
@app.delete('/api/files/{file_id}')
def delete(file_id:str,user=Depends(current),db=Depends(database)):
    f=locked_file(db,user,file_id,True);f.deleted=True;event(db,user,'FILE_DELETED',f);db.commit();return {'ok':True}
@app.get('/api/files/{file_id}/versions/{version_id}/download')
def download(file_id:str,version_id:str,user=Depends(current),db=Depends(database)):
    f,v,data=release(db,user,file_id,version_id)
    return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(f.name,safe=''),'Content-Security-Policy':"sandbox; default-src 'none'"})
@app.get('/api/files/{file_id}/versions/{version_id}/preview')
def preview(file_id:str,version_id:str,user=Depends(current),db=Depends(database)):
    f,v,data=release(db,user,file_id,version_id,purpose='preview')
    allowed = {'application/pdf','text/plain','text/csv','application/json','image/png','image/jpeg'}
    if v.mime not in allowed: raise HTTPException(415,'This format is not supported by the reader')
    # Bytes are consumed by the in-app reader, never navigated to as active HTML.
    return Response(data,media_type=v.mime,headers={
        'Content-Disposition':'inline', 'Cache-Control':'no-store',
        'Content-Security-Policy':"sandbox; default-src 'none'"})

@app.post('/api/files/{file_id}/share')
def share(file_id:str,body:Share,user=Depends(current),db=Depends(database)):
    f=locked_file(db,user,file_id,True)
    target=db.scalar(select(User).where(User.email==body.email.lower(),User.tenant_id==user.tenant_id))
    if not target: raise HTTPException(404,'Workspace member not found')
    perm=db.scalar(select(Permission).where(Permission.file_id==f.id,Permission.user_id==target.id))
    if perm: perm.active=True;perm.can_download=body.can_download
    else: db.add(Permission(tenant_id=user.tenant_id,file_id=f.id,user_id=target.id,can_download=body.can_download))
    event(db,user,'ACCESS_GRANTED',f,target_id=target.id,access='read_download' if body.can_download else 'view_only');edge(db,user.tenant_id,'user:'+target.id,'file:'+f.id,'USER_SHARED_FILE');db.commit();return {'ok':True}
@app.delete('/api/files/{file_id}/share/{user_id}')
def revoke(file_id:str,user_id:str,user=Depends(current),db=Depends(database)):
    f=locked_file(db,user,file_id,True)
    p=db.scalar(select(Permission).where(Permission.file_id==f.id,Permission.user_id==user_id))
    if p: p.active=False
    event(db,user,'ACCESS_REVOKED',f,target_id=user_id);edge(db,user.tenant_id,'user:'+user_id,'file:'+f.id,'USER_PERMISSION_REVOKED');db.commit();return {'ok':True}
@app.get('/api/events')
def events(user=Depends(current),db=Depends(database)):
    ids=authorized_files(user).with_only_columns(File.id)
    return [serialize(e) for e in db.scalars(select(Event).where(Event.tenant_id==user.tenant_id,or_(Event.file_id.in_(ids),Event.actor_id==user.id)).order_by(Event.created.desc()).limit(100))]
@app.get('/api/scheduler')
def scheduler(user=Depends(researcher),db=Depends(database)):
    return dict(strategy=db.get(Tenant,user.tenant_id).strategy,capacity=settings().worker_capacity,
        jobs=[serialize(j) for j in db.scalars(select(Job).where(Job.tenant_id==user.tenant_id).order_by(Job.created.desc()).limit(300))],
        decisions=[serialize(d) for d in db.scalars(select(Decision).where(Decision.tenant_id==user.tenant_id).order_by(Decision.created.desc()).limit(100))],
        models=model_statuses())
@app.post('/api/scheduler/strategy')
def strategy(body:Strategy,user=Depends(researcher),db=Depends(database)):
    if body.strategy in ('lightgbm','tgn') and not next(m for m in model_statuses() if m['name']==body.strategy)['available']: raise HTTPException(409,'Train and evaluate a compatible complete checkpoint first')
    db.get(Tenant,user.tenant_id).strategy=body.strategy;db.commit();return {'ok':True}
@app.post('/api/policy/advance')
def advance(user=Depends(researcher),db=Depends(database)):
    # Lock all files before policy row, matching the release/worker lock order.
    list(db.scalars(select(File).where(File.tenant_id==user.tenant_id).order_by(File.id).with_for_update()))
    p=policy(db,user.tenant_id,True);p.epoch+=1
    db.add(PolicyEpoch(tenant_id=user.tenant_id,epoch=p.epoch))
    for v in db.scalars(select(Version).where(Version.tenant_id==user.tenant_id,Version.status!='QUARANTINED')):
        v.status='EVIDENCE_STALE';v.generation+=1;enqueue(db,v,p)
    event(db,user,'POLICY_INVALIDATED',epoch=p.epoch);db.commit();return {'epoch':p.epoch}
@app.get('/api/graph')
def graph(node:str|None=None,before:float|None=None,limit:int=80,user=Depends(researcher),db=Depends(database)):
    q=select(GraphEvent).where(GraphEvent.tenant_id==user.tenant_id,GraphEvent.created<=(before or now()))
    if node: q=q.where(or_(GraphEvent.source==node,GraphEvent.target==node))
    rows=list(db.scalars(q.order_by(GraphEvent.created.desc()).limit(max(1,min(limit,150)))))
    nodes=sorted({x for r in rows for x in (r.source,r.target)})
    return {'nodes':[{'id':n,'type':n.split(':')[0]} for n in nodes],'edges':[serialize(r) for r in rows]}
@app.get('/api/research')
def research(user=Depends(researcher),db=Depends(database)):
    return [serialize(e) for e in db.scalars(select(Experiment).where(Experiment.tenant_id==user.tenant_id).order_by(Experiment.created.desc()))]
@app.get('/api/research/csv')
def research_csv(user=Depends(researcher),db=Depends(database)):
    stream=io.StringIO();w=csv.writer(stream);w.writerow(['run_id','configuration','results'])
    for r in research(user,db): w.writerow([r['id'],json.dumps(r['config']),json.dumps(r['results'])])
    return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="prooflane-results.csv"'})
@app.post('/api/assistant')
def assistant(body:Question,user=Depends(current),db=Depends(database)): return answer(db,user,body.question)

@app.get('/api/models/cnn')
def cnn_status(user=Depends(researcher)):
    path=Path(settings().model_directory)/'cnn'/'manifest.json'
    return {'available':path.is_file(),'enabled_for_release':False,'manifest':json.loads(path.read_text()) if path.is_file() else None}
@app.post('/api/models/cnn/infer')
def cnn_infer(file:UploadFile=Upload(...),user=Depends(researcher)):
    directory=Path(settings().model_directory)/'cnn'
    if not (directory/'manifest.json').is_file(): raise HTTPException(409,'No compatible CNN checkpoint; experimental module disabled')
    data=file.file.read(settings().max_upload_bytes+1)
    if len(data)>settings().max_upload_bytes:raise HTTPException(413,'File exceeds upload limit')
    from ml.cnn.infer import infer
    return infer(data,directory)


def model_statuses():
    from ml.registry import status
    return [status(Path(settings().model_directory)/name,name) for name in ('lightgbm','tgn')]

@app.get('/api/research/models')
def research_models(user=Depends(researcher)):
    return model_statuses()

@app.get('/api/assistant/status')
def assistant_status(user=Depends(current)):
    s=settings()
    return {'configured':bool(s.anthropic_api_key and s.anthropic_model),
            'provider':s.llm_provider,'model':s.anthropic_model or None,
            'availability':'checked against account when answering'}

@app.post('/api/research/import-local')
def import_local_results(user=Depends(researcher),db=Depends(database)):
    import math
    path=Path(settings().research_results_path)
    if not path.is_file():raise HTTPException(404,'No completed experiment run is available to import')
    raw=path.read_bytes()
    if len(raw)>5*1024*1024:raise HTTPException(413,'Experiment report exceeds the allowed size')
    try:
        report=json.loads(raw)
        if not isinstance(report.get('results'),dict) or not report['results']:raise ValueError('Missing scheduler results')
        if not isinstance(report.get('seed'),int) or not isinstance(report.get('workers'),int):raise ValueError('Missing experiment configuration')
        if report['workers']<1:raise ValueError('Invalid worker count')
        for strategy,metrics in report['results'].items():
            if strategy not in ('fifo','edf','rule','lightgbm','tgn'):raise ValueError('Unknown scheduling method')
            for value in metrics.values():
                if isinstance(value,(float,int)) and not math.isfinite(value):raise ValueError('Invalid metric')
    except (ValueError,TypeError,AttributeError):raise HTTPException(422,'Experiment report is incomplete or invalid')
    fingerprint=hashlib.sha256(raw).hexdigest()
    for existing in db.scalars(select(Experiment).where(Experiment.tenant_id==user.tenant_id)):
        if existing.config.get('report_sha256')==fingerprint:return {'id':existing.id,'imported':False}
    run=Experiment(tenant_id=user.tenant_id,config={'kind':'recorded held-out scheduling comparison','seed':report['seed'],
        'workers':report['workers'],'dataset_sha256':report.get('dataset_sha256'),
        'model_checkpoints':report.get('model_checkpoints',{}),'report_sha256':fingerprint},results=report)
    db.add(run);db.flush()
    for strategy,metrics in report['results'].items():
        for name,value in metrics.items():
            if isinstance(value,(int,float)) and not isinstance(value,bool):db.add(Metric(run_id=run.id,name=strategy+'.'+name,value=value))
    db.commit();return {'id':run.id,'imported':True}
