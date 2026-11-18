"""Train genuine workload models and compare five schedulers on held-out rows."""
import argparse
import csv
import json
from pathlib import Path
import time
from ml.data import load,split
from ml.registry import manifest


def compare(dataset,models,output,seed=17,workers=2):
    import numpy as np
    import lightgbm as lgb
    import torch
    from ml.temporal_gnn.model import TemporalGraph
    from benchmarks.run import simulate
    from ml.registry import sha256
    rows=split(load(dataset))[2]
    if not rows:raise ValueError('Held-out workload is empty')
    predictions={};overhead={};versions={}
    for method in ['lightgbm','tgn']:
        directory=Path(models)/method;m=manifest(directory,method);versions[method]=m['model_version']
        print(json.dumps({'phase':'held-out inference','method':method,'jobs':len(rows)}),flush=True)
        if method=='lightgbm':
            heads=[lgb.Booster(model_file=str(directory/f'head-{i}.txt')) for i in range(2)]
            x=np.array([r['x'] for r in rows]);start=time.perf_counter()
            output_heads=[h.predict(x) for h in heads];values=list(zip(*output_heads));elapsed=time.perf_counter()-start
        else:
            model=TemporalGraph(memory=m['memory'],graph=m['graph'])
            model.load_state_dict(torch.load(directory/'weights.pt',map_location='cpu',weights_only=True));model.eval();values=[]
            start=time.perf_counter()
            with torch.no_grad():
                for row in rows:
                    values.append(model.predict_context(row['src'],row['dst'],row['time'],torch.tensor(row['x'],dtype=torch.float32),row['context']).tolist())
            elapsed=time.perf_counter()-start
        if not np.isfinite(np.asarray(values)).all():raise ValueError('Non-finite held-out model output')
        predictions[method]={r['id']:(float(p[0]),float(p[1])) for r,p in zip(rows,values)}
        overhead[method]={'total_seconds':elapsed,'seconds_per_job':elapsed/len(rows)}
    results={}
    for strategy in ['fifo','edf','rule','lightgbm','tgn']:
        print(json.dumps({'phase':'queue simulation','strategy':strategy}),flush=True)
        start=time.perf_counter();result=simulate(rows,strategy,workers,predictions.get(strategy))
        result['simulation_execution_seconds']=time.perf_counter()-start
        result['inference_seconds']=overhead.get(strategy,{}).get('total_seconds',0.)
        results[strategy]=result
    report={'dataset':str(dataset),'dataset_sha256':sha256(dataset),'seed':seed,'workers':workers,
        'dataset_provenance':sorted({r.get('provenance','unspecified') for r in rows}),'evaluation':'held-out temporal test partition only','jobs':len(rows),'model_checkpoints':versions,
        'inference':overhead,'results':results,
        'limitations':['Synthetic service times and requests; no real-world generalization claim.',
            'Predictions are cached at arrival for both learned schedulers; inference overhead is measured separately and is not added to simulated job delay.',
            'Waiting time is verification queue delay, not a measured user download delay.',
            'Single-seed comparison; no confidence interval or superiority claim.',
            'This scheduling simulation does not establish policy-invalid release counts under live faults.']}
    directory=Path(output);directory.mkdir(parents=True,exist_ok=True)
    (directory/'results.json').write_text(json.dumps(report,indent=2))
    with (directory/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['strategy']+list(next(iter(results.values())).keys()));writer.writeheader()
        for strategy,row in results.items():writer.writerow({'strategy':strategy,**row})
    print(json.dumps(report,indent=2),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir',default='artifacts/dataset-v2')
    parser.add_argument('--models',default='artifacts/models')
    parser.add_argument('--results',default='artifacts/results-v2')
    parser.add_argument('--seed',type=int,default=17)
    parser.add_argument('--epochs',type=int,default=10)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--ablations',action='store_true')
    args=parser.parse_args()
    from benchmarks.generate import generate
    from ml.train import train
    dataset=Path(args.dataset_dir)/'workload.jsonl'
    if not dataset.is_file():generate(args.dataset_dir,args.seed)
    rows=load(dataset)
    if not all('synthetic-v2' in r.get('provenance','') or r.get('provenance','').startswith('application:') for r in rows):
        raise ValueError('Regenerate the causal v2 dataset or export actual scheduling snapshots')
    for method in ['lightgbm','tgn']:
        train(dataset,method,Path(args.models)/method,args.seed,args.epochs)
    if args.ablations:
        train(dataset,'tgn',Path(args.models)/'tgn-no-memory',args.seed,args.epochs,memory=False)
        train(dataset,'tgn',Path(args.models)/'tgn-no-graph',args.seed,args.epochs,graph=False)
    compare(dataset,args.models,args.results,args.seed,args.workers)

if __name__=='__main__':main()
