"""Local trusted checkpoint registry. Incompatible or changed files are unavailable."""
import hashlib
import json
from pathlib import Path
from .context import INPUT_SCHEMA,MAX_EVENTS
from .data import FEATURES,HORIZON

def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024):digest.update(chunk)
    return digest.hexdigest()

def version(method,checkpoints):
    return hashlib.sha256(json.dumps({'method':method,'checkpoints':checkpoints,'schema':INPUT_SCHEMA},sort_keys=True).encode()).hexdigest()[:16]

def manifest(directory,method):
    directory=Path(directory)
    result=json.loads((directory/'manifest.json').read_text())
    if result.get('method')!=method or result.get('input_schema')!=INPUT_SCHEMA or result.get('max_context_events')!=MAX_EVENTS or result.get('features')!=FEATURES or result.get('horizon')!=HORIZON:
        raise ValueError('Checkpoint feature schema mismatch')
    names=['head-0.txt','head-1.txt'] if method=='lightgbm' else ['weights.pt'] if method=='tgn' else []
    if not names or set(result.get('checkpoints',{}))!=set(names):raise ValueError('Incomplete checkpoint manifest')
    if any(sha256(directory/name)!=result['checkpoints'][name] for name in names):raise ValueError('Checkpoint hash mismatch')
    if result.get('model_version')!=version(method,result['checkpoints']):raise ValueError('Model identity mismatch')
    return result

def status(directory,method):
    try:
        m=manifest(directory,method)
        return {'name':method,'available':True,'model_version':m['model_version'],'metrics':m['metrics'],'seed':m['seed'],'dataset_sha256':m['dataset_sha256'],'provenance':m.get('provenance',[])}
    except (OSError,ValueError,KeyError,TypeError):
        return {'name':method,'available':False,'reason':'No compatible, complete trained checkpoint'}
