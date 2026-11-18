"""Read-only model inference; outputs are consumed solely for queue ordering."""
import json
from pathlib import Path
from sqlalchemy import select
from .db import Job,Version,Event
from .config import settings

def predict_jobs(db,jobs,method,at):
    from ml.registry import manifest as read_manifest
    from .features import job_features,graph_context
    directory=Path(settings().model_directory)/method
    manifest=read_manifest(directory,method)
    xs=[job_features(db,j,at) for j in jobs]
    if method=='lightgbm':
        import lightgbm as lgb
        import numpy as np
        array=np.array(xs)
        heads=[lgb.Booster(model_file=str(directory/f'head-{i}.txt')).predict(array) for i in range(2)]
        predictions=list(zip(*heads))
    else:
        import torch
        from ml.temporal_gnn.model import TemporalGraph
        from .db import GraphEvent
        model=TemporalGraph(memory=manifest['memory'],graph=manifest['graph'])
        model.load_state_dict(torch.load(directory/'weights.pt',map_location='cpu',weights_only=True));model.eval()
        context=graph_context(db,jobs[0].tenant_id,at)
        with torch.no_grad():
            predictions=[model.predict_context('job:'+j.id,'version:'+j.version_id,at,
                         torch.tensor(x,dtype=torch.float32),context).tolist() for j,x in zip(jobs,xs)]
    import math
    if any(not all(math.isfinite(float(v)) for v in p) for p in predictions): raise ValueError('Non-finite prediction')
    return {j.id:(float(p[0]),float(p[1])) for j,p in zip(jobs,predictions)},manifest['model_version']
