"""Specification conformance and paired discrete-event queue experiments.
Simulation metrics are not live-service benchmark results.
"""
import argparse,csv,json,time,statistics,heapq,random
from pathlib import Path
from benchmarks.generate import SCENARIOS
from benchmarks.oracle import scenario

def conformance():
    from prooflane.security import ReleaseFacts,release_denial
    results=[]
    for name in SCENARIOS:
        oracle,target,at=scenario(name)
        # Translate fixture facts into gateway inputs without using oracle.permits().
        scan=oracle.clean_versions.get(target)
        f=ReleaseFacts(oracle.permission and oracle.tenant_match,target==oracle.current,'APPROVED' if scan else 'PENDING',bool(scan),bool(scan and scan[1]==oracle.digests.get(target)),bool(scan and scan[0]==oracle.epoch),bool(scan and scan[1]==oracle.digests.get(target)),oracle.valid_until)
        actual=release_denial(f,at) is None;expected=oracle.permits(target,at)
        results.append({'scenario':name,'expected_release':expected,'actual_release':actual,'pass':expected==actual})
    return results

def simulate(rows,strategy,workers=2,predictions=None):
    if not rows or workers<1: raise ValueError("Nonempty workload and positive capacity required")
    from prooflane.scheduling import Candidate,rank
    queue=[];available=[rows[0]['time']]*workers;waits=[];misses=0;busy=0.;backlog=0
    i=0;t=rows[0]['time'];start=t
    while i<len(rows) or queue:
        while i<len(rows) and rows[i]['time']<=t:
            queue.append(rows[i]);i+=1
        free=[w for w,v in enumerate(available) if v<=t]
        while free and queue:
            candidates=[Candidate(r['id'],'synthetic',r['time'],r.get('deadline',r['time']+300),max(.1,r['x'][0]/10)) for r in queue]
            selected=rank(candidates,strategy,t,predictions)[0];r=next(r for r in queue if r['id']==selected.id);queue.remove(r)
            w=free.pop();duration=r['y'][0];available[w]=t+duration;busy+=duration
            delay=t-r['time'];waits.append(delay);misses+=int(t+duration>r.get('deadline',r['time']+300))
        backlog=max(backlog,len(queue))
        future=[v for v in available if v>t]
        if i<len(rows): future.append(rows[i]['time'])
        if future: t=min(future)
        elif queue: raise RuntimeError('Simulation made no progress')
    ordered=sorted(waits)
    return {'mean_wait_seconds':statistics.mean(waits),'p95_wait_seconds':ordered[int(.95*(len(ordered)-1))],
            'deadline_misses':misses,'worker_utilization':busy/(workers*max(1,max(available)-start)),'peak_backlog':backlog,
            'verification_seconds':busy,'jobs':len(rows),'provenance':'discrete-event simulation; no live object-store or scanner operations'}

def main(dataset,output):
    start=time.perf_counter();cpu=time.process_time();out=Path(output);out.mkdir(parents=True,exist_ok=True)
    security=conformance();(out/'conformance.json').write_text(json.dumps(security,indent=2))
    rows=[json.loads(l) for l in Path(dataset).read_text().splitlines()]
    results={s:simulate(rows,s) for s in ('fifo','edf','rule')}
    report={'dataset':str(dataset),'security_conformance_passed':sum(r['pass'] for r in security),'security_conformance_total':len(security),'results':results,'execution_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'limitations':['Conformance tests exercise a pure gateway predicate, not concurrent PostgreSQL transactions.','ML scheduler and integrity-policy comparisons require further live experiments.','Synthetic durations are generated targets, not measured scans.']}
    (out/'results.json').write_text(json.dumps(report,indent=2))
    with (out/'results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['strategy']+list(next(iter(results.values())).keys()));w.writeheader()
        for s,r in results.items(): w.writerow({'strategy':s,**r})
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('--output',default='artifacts/results');a=p.parse_args();main(a.dataset,a.output)
