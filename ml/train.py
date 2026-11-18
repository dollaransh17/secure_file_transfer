"""Train separate LightGBM/TGN alternatives; metrics always come from held-out predictions."""
import argparse
import json
import time
import random
from pathlib import Path
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ml.data import load, split, FEATURES, HORIZON

def metrics(y,p,latency):
    y=np.array(y);p=np.array(p)
    return {'duration_mae':float(mean_absolute_error(y[:,0],p[:,0])),
            'duration_rmse':float(np.sqrt(mean_squared_error(y[:,0],p[:,0]))),
            'demand_mae':float(mean_absolute_error(y[:,1],p[:,1])),
            'demand_bias':float(np.mean(p[:,1]-y[:,1])),
            'prediction_seconds_per_job':latency/len(y)}

def train(path,method,output,seed=17,epochs=30,memory=True,graph=True):
    random.seed(seed);np.random.seed(seed)
    rows=load(path);training,validation,test=split(rows)
    if min(map(len,(training,validation,test)))<5: raise ValueError('Insufficient purged temporal splits')
    print(json.dumps({'phase':'training','method':method,'seed':seed,
                      'split_sizes':list(map(len,(training,validation,test)))}),flush=True)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    log=[]
    if method=='lightgbm':
        import lightgbm as lgb
        from sklearn.multioutput import MultiOutputRegressor
        # Separate target estimators. Fixed hyperparameters, no tuning on test data.
        model=MultiOutputRegressor(lgb.LGBMRegressor(n_estimators=100,num_leaves=15,random_state=seed,verbosity=-1,n_jobs=1))
        model.fit([r['x'] for r in training],[r['y'] for r in training])
        val=model.predict([r['x'] for r in validation])
        log.append({'validation':metrics([r['y'] for r in validation],val,0)})
        start=time.perf_counter();pred=model.predict([r['x'] for r in test]);elapsed=time.perf_counter()-start
        for i,estimator in enumerate(model.estimators_): estimator.booster_.save_model(str(out/f'head-{i}.txt'))
    else:
        import torch
        from ml.temporal_gnn.model import TemporalGraph
        torch.manual_seed(seed);torch.set_num_threads(1)
        model=TemporalGraph(memory=memory,graph=graph);optimizer=torch.optim.Adam(model.parameters(),lr=.002)
        best=float('inf');patience=0
        if any('context' not in row for row in rows):
            raise ValueError('TGN requires causal typed context snapshots; regenerate/export the dataset')
        for epoch in range(epochs):
            model.train();losses=[]
            for r in training:
                optimizer.zero_grad()
                x=torch.tensor(r['x'],dtype=torch.float32)
                p=model.predict_context(r['src'],r['dst'],r['time'],x,r['context'])
                loss=torch.nn.functional.smooth_l1_loss(torch.log1p(p),torch.log1p(torch.tensor(r['y'],dtype=torch.float32)))
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
                optimizer.step();losses.append(loss.item());model.reset_state()
            model.eval();ys=[];ps=[]
            with torch.no_grad():
                for r in validation:
                    x=torch.tensor(r['x'],dtype=torch.float32)
                    ps.append(model.predict_context(r['src'],r['dst'],r['time'],x,r['context']).tolist());ys.append(r['y'])
            score=metrics(ys,ps,0)['duration_mae']+metrics(ys,ps,0)['demand_mae']
            log.append({'epoch':epoch,'training_loss':float(np.mean(losses)),'validation_loss':score})
            print(json.dumps(log[-1]),flush=True)
            if score<best:
                best=score;patience=0;torch.save(model.state_dict(),out/'weights.pt')
            else: patience+=1
            if patience>=5: break
        model.load_state_dict(torch.load(out/'weights.pt',weights_only=True));model.eval();pred=[];elapsed=0
        with torch.no_grad():
            for r in test:
                x=torch.tensor(r['x'],dtype=torch.float32)
                start=time.perf_counter()
                pred.append(model.predict_context(r['src'],r['dst'],r['time'],x,r['context']).tolist())
                elapsed+=time.perf_counter()-start
    report=metrics([r['y'] for r in test],pred,elapsed)
    import hashlib
    from ml.context import INPUT_SCHEMA,MAX_EVENTS
    manifest={'input_schema':INPUT_SCHEMA,'max_context_events':MAX_EVENTS,'method':method,'seed':seed,'dataset_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'features':FEATURES,
              'horizon':HORIZON,'memory':memory,'graph':graph,'split_sizes':list(map(len,(training,validation,test))),'metrics':report,'logs':log,
              'limitation':'Synthetic targets if input provenance is synthetic; no real-world generalization established.'}
    from ml.registry import sha256,version
    names=['head-0.txt','head-1.txt'] if method=='lightgbm' else ['weights.pt']
    manifest['checkpoints']={name:sha256(out/name) for name in names}
    manifest['model_version']=version(method,manifest['checkpoints'])
    manifest['provenance']=sorted({r.get('provenance','unspecified') for r in rows})
    temporary=out/('.manifest-'+str(__import__('uuid').uuid4())+'.tmp')
    temporary.write_text(json.dumps(manifest,indent=2));temporary.replace(out/'manifest.json')
    print(json.dumps(report,indent=2))
    return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('--method',choices=['lightgbm','tgn'],required=True);p.add_argument('--output',required=True);p.add_argument('--seed',type=int,default=17);p.add_argument('--epochs',type=int,default=30);p.add_argument('--no-memory',action='store_true');p.add_argument('--no-graph',action='store_true');a=p.parse_args()
    train(a.dataset,a.method,a.output,a.seed,a.epochs,not a.no_memory,not a.no_graph)
