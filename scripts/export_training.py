"""Export actual scheduling-time snapshots and mature measured targets."""
import argparse
import math
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/api'))
# Script execution also needs the repository's research modules.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select,func
from prooflane.db import SessionLocal,Job,Event,Decision,now
from ml.data import HORIZON
from ml.context import INPUT_SCHEMA,validate_context

def export(tenant,output):
    rows=[];skipped=0
    with SessionLocal() as db:
        jobs=list(db.scalars(select(Job).where(Job.tenant_id==tenant,Job.status=='COMPLETE',Job.duration!=None)))
        for job in jobs:
            decision=db.scalar(select(Decision).where(Decision.job_id==job.id,Decision.tenant_id==tenant)
                               .order_by(Decision.created.desc()))
            if not decision or decision.inputs.get('feature_schema')!=INPUT_SCHEMA:
                skipped+=1;continue
            at=decision.created
            if at+HORIZON>now():continue
            context=decision.inputs['context'];validate_context(context,at)
            demand=db.scalar(select(func.count(Event.id)).where(
                Event.tenant_id==tenant,Event.file_id==job.file_id,
                Event.kind=='DOWNLOAD_AUTHORIZED',Event.created>=at,Event.created<at+HORIZON)) or 0
            rows.append(dict(id=decision.id,time=at,history_until=math.nextafter(at,-math.inf),
                src='job:'+job.id,dst='version:'+job.version_id,
                x=decision.inputs['features'],context=context,y=[job.duration,demand],
                target_end=max(job.completed,at+HORIZON),input_schema=INPUT_SCHEMA,
                provenance='application: persisted scheduling inputs, measured worker duration, authorized request count'))
    rows.sort(key=lambda r:(r['time'],r['id']))
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('\n'.join(json.dumps(r) for r in rows)+ ('\n' if rows else ''))
    print(f'Exported {len(rows)} mature jobs; skipped {skipped} jobs without current scheduling snapshots')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tenant',required=True);p.add_argument('--output',default='artifacts/application-training.jsonl');a=p.parse_args();export(a.tenant,a.output)
