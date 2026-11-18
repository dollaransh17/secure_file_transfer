"""Integration tests with explicit local storage and scanner doubles.
Real PostgreSQL/MinIO/ClamAV smoke tests are separate; these never claim real AV.
"""
import os
os.environ['ANTHROPIC_API_KEY']=''
os.environ['ANTHROPIC_MODEL']=''
os.environ['DATABASE_URL']='sqlite://'
os.environ['STORAGE_BACKEND']='local'
os.environ['ENVIRONMENT']='test'
# Unit integration fixtures use a fixed origin independently of the deployed
# Compose port. Set it before app construction so CORS and CSRF agree.
os.environ['PUBLIC_ORIGIN']='http://localhost:5173'
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from prooflane import db as models
from prooflane import worker
from prooflane.main import app
from prooflane.db import *
from prooflane.scanner import Verdict
from prooflane.storage import storage
from prooflane.config import settings
from prooflane.domain import enqueue,policy
from prooflane.assistant import retrieve

ORIGIN='http://localhost:5173'
class RateRedis:
    def eval(self,*args):return 1
@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    factory=sessionmaker(engine,expire_on_commit=False)
    Base.metadata.create_all(engine)
    def database_override():
        with factory() as db:yield db
    app.dependency_overrides[models.database]=database_override
    monkeypatch.setattr(worker,'SessionLocal',factory)
    monkeypatch.setattr('prooflane.main.Redis.from_url',lambda *args,**kw:RateRedis())
    monkeypatch.setattr(settings(),'local_storage',str(tmp_path/'objects'))
    monkeypatch.setattr(settings(),'model_directory',str(tmp_path/'models'))
    storage.cache_clear()
    yield factory
    app.dependency_overrides.clear();storage.cache_clear();engine.dispose()

def register(email='alice@example.test'):
    c=TestClient(app);r=c.post('/api/auth/register',headers={'Origin':ORIGIN},json={'email':email,'password':'long-test-password'});assert r.status_code==200,r.text
    c.headers.update({'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf']});return c,r.json()['user']
def login(email):
    c=TestClient(app);r=c.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':email,'password':'long-test-password'});assert r.status_code==200
    c.headers.update({'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf']});return c

def uploaded(c,file_id=None):
    r=c.post('/api/files',params={'file_id':file_id} if file_id else {},files={'file':('hello.txt',b'Harmless text','text/plain')});assert r.status_code==200,r.text;return r.json()
def complete(factory,result='CLEAN'):
    with factory() as db: chosen=worker.claim(db,'test-worker')
    assert chosen
    worker.process(*chosen,scan_fn=lambda data:Verdict(result,'ClamAV TEST DOUBLE / test signatures',.01))
    return chosen

def get(c,v):return c.get(f"/api/files/{v['file_id']}/versions/{v['id']}/download")
def shared_pair():
    a,u=register();r=a.post('/api/workspace/members',json={'email':'bob@example.test','password':'long-test-password'});assert r.status_code==200,r.text
    b=login('bob@example.test');return a,b,r.json()

def test_registration_auth_refresh_logout():
    a,u=register();assert a.get('/api/auth/me').json()['user']['id']==u['id']
    old=a.cookies.get('prooflane_session');r=a.post('/api/auth/refresh');assert r.status_code==200
    assert a.cookies.get('prooflane_session')!=old;a.headers['X-CSRF-Token']=r.json()['csrf']
    assert a.post('/api/auth/logout').status_code==200;assert a.get('/api/files').status_code==401

def test_invalid_login_and_csrf():
    a,_=register();assert a.post('/api/auth/login',json={'email':'alice@example.test','password':'wrong-long-password'}).status_code==401
    a.headers['X-CSRF-Token']='bad';assert a.post('/api/files',files={'file':('a.txt',b'a')}).status_code==403

@pytest.mark.parametrize('origin',['http://localhost:5173','http://localhost:5174'])
def test_registration_and_mutations_enforce_configured_origin(monkeypatch,origin):
    monkeypatch.setattr(settings(),'public_origin',origin)
    wrong='http://localhost:5174' if origin.endswith(':5173') else 'http://localhost:5173'
    client=TestClient(app)
    body={'email':'origin-check@example.test','password':'long-test-password'}
    assert client.post('/api/auth/register',headers={'Origin':wrong},json=body).status_code==403
    response=client.post('/api/auth/register',headers={'Origin':origin},json=body)
    assert response.status_code==200,response.text
    headers={'Origin':wrong,'X-CSRF-Token':response.json()['csrf']}
    assert client.post('/api/auth/logout',headers=headers).status_code==403
    assert client.get('/api/auth/me').status_code==200
    headers['Origin']=origin
    assert client.post('/api/auth/logout',headers=headers).status_code==200

def test_expired_session(isolated):
    a,_=register()
    with isolated() as db:
        for s in db.scalars(select(Session)):s.expires=0
        db.commit()
    assert a.get('/api/files').status_code==401

def test_upload_pending_then_exact_download(isolated):
    a,_=register();v=uploaded(a);assert get(a,v).status_code==423
    complete(isolated);r=get(a,v);assert r.status_code==200;assert r.content==b'Harmless text'
    with isolated() as db:assert db.scalar(select(Scan)).digest==v['digest']

def test_owner_storage_location_maps_existing_file_to_s3_without_credentials(monkeypatch):
    a,_=register();v=uploaded(a)
    monkeypatch.setattr(settings(),'storage_backend','s3')
    monkeypatch.setattr(settings(),'s3_endpoint',None)
    monkeypatch.setattr(settings(),'s3_bucket','private-mapping-bucket')
    monkeypatch.setattr(settings(),'aws_region','ap-south-1')
    response=a.get('/api/files/'+v['file_id'])
    assert response.status_code==200
    data=response.json()
    assert data['storage_location']==dict(backend='s3',bucket='private-mapping-bucket',region='ap-south-1',aws_console=True)
    assert data['versions'][0]['storage_key']==v['storage_key']
    assert data['versions'][0]['object_version']==v['object_version']
    assert 's3_secret_key' not in response.text
    outsider,_=register('outsider@example.test')
    assert outsider.get('/api/files/'+v['file_id']).status_code==404

def test_shared_reader_does_not_receive_owner_storage_location():
    a,b,_=shared_pair();v=uploaded(a)
    assert a.post('/api/files/'+v['file_id']+'/share',json={'email':'bob@example.test'}).status_code==200
    data=b.get('/api/files/'+v['file_id']).json()
    assert 'storage_location' not in data

def test_detected_quarantine(isolated):
    a,_=register();v=uploaded(a);complete(isolated,'INFECTED');assert get(a,v).status_code==423
    with isolated() as db:assert db.get(Version,v['id']).status=='QUARANTINED'

@pytest.mark.parametrize('verdict,status,download_status',[('CLEAN','APPROVED',200),('INFECTED','QUARANTINED',423)])
def test_mock_cnn_never_changes_verification_or_release(isolated,monkeypatch,verdict,status,download_status):
    monkeypatch.setattr(settings(),'cnn_mode','mock')
    a,u=register();v=uploaded(a);complete(isolated,verdict)
    details=a.get('/api/files/'+v['file_id']).json()
    assert details['versions'][0]['status']==status
    demo=details['cnn_demo']['result']
    assert demo['mode']=='mock' and demo['release_authority'] is False
    assert demo['digest']==v['digest'] and demo['object_version']==v['object_version']
    assert sum(demo['demo_scores'].values())==100
    assert get(a,v).status_code==download_status
    assert a.post('/api/files/'+v['file_id']+'/cnn-demo').status_code==200
    assert get(a,v).status_code==download_status
    with isolated() as db:
        assert db.get(Version,v['id']).status==status
        assert all(e['kind']!='MOCK_CNN_ANALYSIS' for e in retrieve(db,db.get(User,u['id']),'CNN demo'))

def test_existing_pending_file_demo_does_not_approve_and_replacement_does_not_reuse_it(isolated,monkeypatch):
    monkeypatch.setattr(settings(),'cnn_mode','mock')
    a,_=register();v=uploaded(a)
    assert a.post('/api/files/'+v['file_id']+'/cnn-demo').status_code==200
    assert get(a,v).status_code==423
    v2=uploaded(a,v['file_id'])
    assert a.get('/api/files/'+v['file_id']).json()['cnn_demo']['result'] is None
    assert get(a,v2).status_code==423
    outsider,_=register('outsider-demo@example.test')
    assert outsider.post('/api/files/'+v['file_id']+'/cnn-demo').status_code==404

def test_mock_demo_disabled_without_explicit_setting(monkeypatch):
    monkeypatch.setattr(settings(),'cnn_mode','disabled')
    a,_=register();v=uploaded(a)
    assert a.post('/api/files/'+v['file_id']+'/cnn-demo').status_code==409

def test_scanner_error_never_approves(isolated):
    a,_=register();v=uploaded(a)
    with isolated() as db:chosen=worker.claim(db,'test-worker')
    def fail(data):raise TimeoutError('test')
    worker.process(*chosen,scan_fn=fail);assert get(a,v).status_code==423
    with isolated() as db:assert db.get(Job,chosen[0]).status=='PENDING'

def test_previous_scan_cannot_approve_newer_version(isolated):
    a,b,bob=shared_pair();v1=uploaded(a);complete(isolated);a.post('/api/files/'+v1['file_id']+'/share',json={'email':bob['email']})
    v2=uploaded(a,v1['file_id'])
    # Replayed old completion is fenced by terminal status/token.
    with isolated() as db:j=db.scalar(select(Job).where(Job.version_id==v1['id']));old=(j.id,j.lease_token)
    assert not worker.process(*old,scan_fn=lambda b:Verdict('CLEAN','TEST',.1))
    assert b.get(f"/api/files/{v2['file_id']}/versions/{v2['id']}/preview").status_code==423;assert get(a,v1).status_code==423

def test_late_scan_updates_only_old_version(isolated):
    a,_=register();v1=uploaded(a)
    with isolated() as db:chosen=worker.claim(db,'slow')
    v2=uploaded(a,v1['file_id']);worker.process(*chosen,scan_fn=lambda b:Verdict('CLEAN','TEST',.1))
    assert get(a,v2).status_code==423
    with isolated() as db:assert db.get(Version,v2['id']).status=='PENDING'

def test_sharing_and_revocation(isolated):
    a,b,bob=shared_pair();v=uploaded(a);complete(isolated);assert get(b,v).status_code==403
    assert a.post('/api/files/'+v['file_id']+'/share',json={'email':bob['email']}).status_code==200;assert get(b,v).status_code==403;assert b.get(f"/api/files/{v['file_id']}/versions/{v['id']}/preview").status_code==200
    assert a.delete(f"/api/files/{v['file_id']}/share/{bob['id']}").status_code==200;assert get(b,v).status_code==403

def test_cross_tenant_and_permission_mutation_denied(isolated):
    a,_=register();v=uploaded(a);b,_=register('outsider@example.test')
    assert get(b,v).status_code==404;assert b.get('/api/files/'+v['file_id']).status_code==404
    assert a.post('/api/files/'+v['file_id']+'/share',json={'email':'outsider@example.test'}).status_code==404

def test_nonowner_cannot_rename_delete_share():
    a,b,bob=shared_pair();v=uploaded(a);a.post('/api/files/'+v['file_id']+'/share',json={'email':bob['email']})
    assert b.patch('/api/files/'+v['file_id'],json={'name':'other.txt'}).status_code==403
    assert b.delete('/api/files/'+v['file_id']).status_code==403
    assert b.post('/api/files/'+v['file_id']+'/share',json={'email':bob['email']}).status_code==403

def test_integrity_mismatch(isolated):
    a,_=register();v=uploaded(a);complete(isolated)
    with isolated() as db:version=db.get(Version,v['id']);path=storage().root/( __import__('hashlib').sha256(version.storage_key.encode()).hexdigest()+'-'+version.object_version)
    path.write_bytes(b'tampered');assert get(a,v).status_code==423

def test_expiry_and_policy_epoch(isolated):
    a,_=register();v=uploaded(a);complete(isolated)
    with isolated() as db:db.scalar(select(Scan)).expires=0;db.commit()
    assert get(a,v).status_code==423
    assert a.post('/api/policy/advance').status_code==200;assert get(a,v).status_code==423

def test_duplicate_work_coalesces(isolated):
    a,_=register();v=uploaded(a)
    with isolated() as db:
        version=db.get(Version,v['id']);p=policy(db,version.tenant_id)
        assert enqueue(db,version,p).id==enqueue(db,version,p).id;db.commit()
        assert len(list(db.scalars(select(Job))))==1

def test_stale_worker_token_rejected(isolated):
    a,_=register();v=uploaded(a)
    with isolated() as db:chosen=worker.claim(db,'first')
    assert not worker.process(chosen[0],'wrong-token',scan_fn=lambda b:Verdict('CLEAN','TEST',.1))
    assert get(a,v).status_code==423

def test_worker_crash_recovered(isolated):
    a,_=register();v=uploaded(a)
    with isolated() as db:
        chosen=worker.claim(db,'crashed');db.get(Job,chosen[0]).lease_until=0;db.commit();worker.reconcile(db)
        assert db.get(Job,chosen[0]).status=='PENDING'

def test_model_unavailable_and_fallback(isolated):
    a,u=register();v=uploaded(a)
    assert a.post('/api/scheduler/strategy',json={'strategy':'tgn'}).status_code==409
    with isolated() as db:
        db.get(Tenant,u['tenant_id']).strategy='tgn';db.commit();chosen=worker.claim(db,'fallback');assert chosen
        assert db.scalar(select(Decision)).strategy=='edf'

def test_rag_filters_revoked_records(isolated):
    a,b,bob=shared_pair();v=uploaded(a)
    assert b.post('/api/assistant',json={'question':'upload'}).json()['events']==[]
    a.post('/api/files/'+v['file_id']+'/share',json={'email':bob['email']})
    assert b.post('/api/assistant',json={'question':'upload'}).json()['events']
    a.delete(f"/api/files/{v['file_id']}/share/{bob['id']}")
    assert b.post('/api/assistant',json={'question':'upload'}).json()['events']==[]

def test_invalid_type_and_spoofed_pdf():
    a,_=register()
    for name,data in [('x.exe',b'MZ'),('x.pdf',b'not a pdf'),('x.json',b'not json'),('x.txt',b'\0')]:
        assert a.post('/api/files',files={'file':(name,data)}).status_code==415

def test_evidence_expires_during_object_read(isolated,monkeypatch):
    a,_=register();v=uploaded(a);complete(isolated)
    original=storage().read
    def slow_read(key,version):
        data=original(key,version)
        with isolated() as db:
            for scan in db.scalars(select(Scan)):scan.expires=0
            db.commit()
        # Move gateway decision clock past the original loaded expiry too.
        monkeypatch.setattr('prooflane.domain.now',lambda:time.time()+7200)
        return data
    monkeypatch.setattr(storage(),'read',slow_read)
    assert get(a,v).status_code==423

def test_retry_limit_dead_letter(isolated):
    a,_=register();v=uploaded(a)
    def fail(data):raise TimeoutError('test')
    for attempt in range(3):
        with isolated() as db:
            j=db.scalar(select(Job));j.available=0;db.commit();chosen=worker.claim(db,'retry-worker')
        worker.process(*chosen,scan_fn=fail)
    with isolated() as db:
        assert db.scalar(select(Job)).status=='DEAD';assert db.get(Version,v['id']).status=='FAILED'
    assert get(a,v).status_code==423

def test_old_policy_completion_cannot_reapprove(isolated):
    a,_=register();v=uploaded(a)
    with isolated() as db:chosen=worker.claim(db,'old-policy')
    assert a.post('/api/policy/advance').status_code==200
    assert not worker.process(*chosen,scan_fn=lambda data:Verdict('CLEAN','TEST',.1))
    assert get(a,v).status_code==423

def test_scheduler_persists_causal_features_and_graph(isolated):
    from ml.context import validate_context
    a,_=register();uploaded(a)
    with isolated() as db:
        chosen=worker.claim(db,'snapshot-test');assert chosen
        decision=db.scalar(select(Decision).where(Decision.job_id==chosen[0]))
        assert decision.inputs['feature_schema']==2
        assert len(decision.inputs['features'])==8
        assert decision.inputs['features'][5]==1 # Queue length before claiming.
        assert decision.inputs['features'][6]==0 # Attempt count before increment.
        validate_context(decision.inputs['context'],decision.created)

def test_research_import_is_scoped_and_idempotent(isolated,tmp_path,monkeypatch):
    import json
    report=tmp_path/'results.json'
    report.write_text(json.dumps({'seed':17,'workers':2,'dataset_sha256':'a'*64,'results':{'fifo':{'mean_wait_seconds':1.2,'p95_wait_seconds':3.4,'deadline_misses':0,'worker_utilization':.5}}}))
    monkeypatch.setattr(settings(),'research_results_path',str(report))
    a,_=register()
    first=a.post('/api/research/import-local');assert first.status_code==200;assert first.json()['imported']
    second=a.post('/api/research/import-local');assert not second.json()['imported'];assert second.json()['id']==first.json()['id']
    b,_=register('research-other@example.test')
    assert b.get('/api/research').json()==[]

def test_storage_notification_duplicate_coalesces_without_approval(isolated):
    from prooflane.storage_events import apply
    a,_=register();v=uploaded(a)
    with isolated() as db:
        version=db.get(Version,v['id'])
        record={'key':version.storage_key,'object_version':version.object_version,'event_key':'e'*64}
        assert apply(db,record)=='recorded';db.commit()
        assert apply(db,record)=='duplicate';db.commit()
        assert len(list(db.scalars(select(Job))))==1
        assert db.get(Version,v['id']).status=='PENDING'


def test_view_only_preview_enforces_evidence_integrity_and_revocation(isolated):
    a,b,bob=shared_pair();v=uploaded(a)
    path=f"/api/files/{v['file_id']}/versions/{v['id']}/preview"
    assert b.get(path).status_code==403
    assert a.post('/api/files/'+v['file_id']+'/share',json={'email':bob['email']}).status_code==200
    assert get(b,v).status_code==403
    assert b.get(path).status_code==423
    complete(isolated)
    response=b.get(path)
    assert response.status_code==200
    assert response.content==b'Harmless text'
    assert response.headers['content-disposition']=='inline'
    assert response.headers['cache-control']=='no-store'
    assert get(a,v).status_code==200
    assert a.delete(f"/api/files/{v['file_id']}/share/{bob['id']}").status_code==200
    assert b.get(path).status_code==403


def test_view_only_preview_quarantine_expiry_and_tampering(isolated):
    a,b,bob=shared_pair();v=uploaded(a)
    a.post('/api/files/'+v['file_id']+'/share',json={'email':bob['email']})
    path=f"/api/files/{v['file_id']}/versions/{v['id']}/preview"
    complete(isolated,result='INFECTED')
    assert b.get(path).status_code==423
    v=uploaded(a,v['file_id']);complete(isolated)
    path=f"/api/files/{v['file_id']}/versions/{v['id']}/preview"
    assert b.get(path).status_code==200
    with isolated() as db:
        scan=db.scalar(select(Scan).where(Scan.version_id==v['id']));scan.expires=0;db.commit()
    assert b.get(path).status_code==423
    v=uploaded(a,v['file_id']);complete(isolated)
    with isolated() as db:
        version=db.get(Version,v['id'])
        path_on_disk=storage().root/( __import__('hashlib').sha256(version.storage_key.encode()).hexdigest()+'-'+version.object_version)
    path_on_disk.write_bytes(b'tampered')
    assert b.get(f"/api/files/{v['file_id']}/versions/{v['id']}/preview").status_code==423


def test_separate_download_grant_upgrade_and_downgrade(isolated):
    a,b,bob=shared_pair();v=uploaded(a);complete(isolated)
    share='/api/files/'+v['file_id']+'/share'
    preview=f"/api/files/{v['file_id']}/versions/{v['id']}/preview"
    assert a.post(share,json={'email':bob['email']}).status_code==200
    assert get(b,v).status_code==403
    assert b.get(preview).status_code==200
    assert b.post(share,json={'email':bob['email'],'can_download':True}).status_code==403
    assert a.post(share,json={'email':bob['email'],'can_download':True}).status_code==200
    assert get(b,v).status_code==200
    assert b.get(preview).status_code==200
    assert a.post(share,json={'email':bob['email'],'can_download':False}).status_code==200
    assert get(b,v).status_code==403
    assert b.get(preview).status_code==200
    assert a.post(share,json={'email':bob['email'],'can_download':True}).status_code==200
    assert a.delete(f"{share}/{bob['id']}").status_code==200
    assert get(b,v).status_code==403
    assert b.get(preview).status_code==403
