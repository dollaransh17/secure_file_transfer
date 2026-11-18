"""Explicitly import an actual local benchmark report into a workspace."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/api'))
from prooflane.db import SessionLocal,Tenant,Experiment,Metric
p=argparse.ArgumentParser();p.add_argument('--tenant',required=True);p.add_argument('--results',default='artifacts/results/results.json');a=p.parse_args()
r=json.loads(Path(a.results).read_text())
with SessionLocal() as db:
    if not db.get(Tenant,a.tenant):raise SystemExit('Unknown tenant')
    e=Experiment(tenant_id=a.tenant,config={'source':a.results,'dataset':r['dataset'],'kind':'synthetic scheduling simulation','workers':r.get('workers',2),'seed':r.get('seed'),'dataset_sha256':r.get('dataset_sha256'),'model_checkpoints':r.get('model_checkpoints',{})},results=r);db.add(e);db.flush()
    for strategy,values in r['results'].items():
        for name,value in values.items():
            if isinstance(value,(float,int)):db.add(Metric(run_id=e.id,name=strategy+'.'+name,value=value))
    db.commit();print(e.id)
