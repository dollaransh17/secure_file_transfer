"""Causal synthetic workload. All observations must precede prediction time.
Targets are parameterized service times and generated request counts, not real scans.
"""
import bisect
from collections import deque
import heapq
import math
import random
from ml.data import features,HORIZON
from ml.context import encode_event,snapshot,INPUT_SCHEMA,MAX_EVENTS


def build(seed=17,files=200,jobs_per_family=600):
    rng=random.Random(seed);rows=[];unseen=max(1,files//5);requests={i:[] for i in range(files+unseen)};at=1000.
    user=lambda file: 'user:'+str(file%20 if file<files else 20+file%5)
    for family in range(6):
        if family:
            # A recorded cooldown lets the prior workload drain and labels mature.
            # Otherwise a saturated queue can purge an entire validation period.
            at+=sum(r['duration'] for r in rows[-jobs_per_family:])+HORIZON+1
        for index in range(jobs_per_family):
            at+=rng.uniform(2,15) if family<3 else rng.uniform(.05,1)
            file=rng.randrange(files,files+unseen) if family==5 else rng.randrange(files);size=int(rng.lognormvariate(9+family*.3,1.5))
            duration=max(.01,size/1e6*(1+family*.3)+rng.uniform(.1,2 if family<3 else 12))
            deadline=at+rng.choice([60,120,300,600])
            count=rng.randint(0,3) if family<3 else rng.randint(1,25)
            if family==4 and index%100<30:count*=5
            requests[file].extend(at+rng.uniform(.001,HORIZON) for _ in range(count))
            rows.append({'id':f'{family}-{index}','time':at,'file':file,'size':size,
                'duration':duration,'deadline':deadline,'family':family})
    for times in requests.values():times.sort()
    # Generate a fixed two-worker historical FIFO trace. Only prior observed
    # completions/requests from this trace may become prediction features.
    workers=[rows[0]['time']]*2;trace=[]
    for r in rows:
        worker=min(range(2),key=lambda n:workers[n]);started=max(r['time'],workers[worker])
        completed=started+r['duration'];workers[worker]=completed
        trace.append((started,completed,r))
    completions=sorted((end,r['id'],r['file'],r['duration']) for _,end,r in trace)
    starts=sorted(start for start,_,_ in trace);ends=sorted(end for _,end,_ in trace)
    graph=[]
    for started,completed,r in trace:
        file=str(r['file']);uid=user(r['file']);vid='version:'+r['id'];jid='job:'+r['id']
        for suffix,src,dst,edge,attrs in [
            ('a',uid,'file:'+file,'USER_UPLOADED_FILE',{}),
            ('b','file:'+file,vid,'FILE_HAS_VERSION',{'size':r['size']}),
            ('c',jid,vid,'JOB_VERIFIES_VERSION',{'size':r['size']})]:
            graph.append(encode_event(src,dst,r['time']-.0001,edge,attrs,r['id']+suffix))
        graph.append(encode_event(vid,'scan:'+r['id'],completed,'VERSION_HAS_SCAN',{'result':'CLEAN'},r['id']+'d'))
    for file,times in requests.items():
        for index,t in enumerate(times):
            graph.append(encode_event(user(file),'file:'+str(file),t,
                'USER_REQUESTED_FILE',{'authorized':True},f'request-{file}-{index}'))
    graph.sort(key=lambda e:(e['time'],e['id']))
    observed=deque(maxlen=MAX_EVENTS);g=0;c=0;previous={};output=[]
    for index,r in enumerate(rows):
        at=r['time'];file=r['file']
        while c<len(completions) and completions[c][0]<at:
            _,_,f,duration=completions[c];previous[f]=duration;c+=1
        while g<len(graph) and graph[g]['time']<at:
            observed.append(graph[g]);g+=1
        times=requests[file]
        left=bisect.bisect_left(times,at-HORIZON);middle=bisect.bisect_left(times,at)
        right=bisect.bisect_left(times,at+HORIZON)
        # Prior arrivals minus observed starts is the historically pending queue.
        prior_started=bisect.bisect_left(starts,at)
        queue=max(0,index-prior_started)
        output.append({'id':r['id'],'time':at,'history_until':math.nextafter(at,-math.inf),
            'src':'job:'+r['id'],'dst':'version:'+r['id'],'logical_file':str(file),'deadline':r['deadline'],
            'x':features(r['size'],at,at,r['deadline'],previous.get(file,0),middle-left,queue,0,2),
            'y':[r['duration'],right-middle],'context':snapshot(list(observed),at),
            'target_end':max(at+HORIZON,next(end for _,end,row in trace if row['id']==r['id'])),
            'family':r['family'],'input_schema':INPUT_SCHEMA,
            'provenance':'synthetic-v2: causal FIFO-history observations; parameterized service times and generated authorized requests'})
    return output
