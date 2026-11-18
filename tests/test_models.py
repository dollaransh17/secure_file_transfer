import json
import pytest

def test_tgn_causal_memory_and_gradients():
    torch=pytest.importorskip('torch');pytest.importorskip('torch_geometric')
    from ml.temporal_gnn.model import TemporalGraph
    torch.manual_seed(17);m=TemporalGraph();x=torch.ones(8)
    p=m('u','v',1,x);assert p.shape==(2,);assert torch.all(p>=0)
    m.observe('u','v',1,x);p2=m('u','v',2,x);p2.sum().backward()
    assert m.gru.weight_ih.grad is not None;assert m.message[0].weight.grad is not None
    with pytest.raises(ValueError):m.observe('u','v',0,x)
    m.reset_state();assert torch.allclose(p,m('u','v',1,x))

def test_lightgbm_training_inference(tmp_path):
    pytest.importorskip('lightgbm');pytest.importorskip('sklearn')
    from ml.train import train
    rows=[{'id':str(i),'time':i*50,'history_until':i*50-1,'src':'u','dst':'v'+str(i%4),'x':[i%5]*8,'y':[1+i%5,i%3]} for i in range(100)]
    path=tmp_path/'data.jsonl';path.write_text('\n'.join(json.dumps(r) for r in rows))
    report=train(path,'lightgbm',tmp_path/'model');assert report['metrics']['duration_mae']>=0
    import lightgbm as lgb
    result=lgb.Booster(model_file=str(tmp_path/'model/head-0.txt')).predict([[1]*8]);assert len(result)==1

def test_tgn_training_inference(tmp_path):
    torch=pytest.importorskip('torch');pytest.importorskip('torch_geometric');pytest.importorskip('sklearn')
    from ml.train import train
    rows=[{'id':str(i),'time':i*50,'history_until':i*50-1,'src':'u','dst':'v'+str(i%4),'x':[i%5]*8,'y':[1+i%5,i%3]} for i in range(100)]
    path=tmp_path/'data.jsonl';path.write_text('\n'.join(json.dumps(r) for r in rows))
    from ml.context import encode_event,snapshot
    history=[]
    for r in rows:
        r['src']='user:u';r['dst']='version:'+r['dst']
        r['context']=snapshot(history,r['time'])
        history.append(encode_event(r['src'],r['dst'],r['time'],'USER_REQUESTED_FILE',{'authorized':True},r['id']))
    path.write_text('\n'.join(json.dumps(r) for r in rows))
    report=train(path,'tgn',tmp_path/'model',epochs=2);assert report['metrics']['duration_mae']>=0
    assert (tmp_path/'model/weights.pt').exists()
