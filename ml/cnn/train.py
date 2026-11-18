import argparse,json,random
from pathlib import Path
import torch
from .model import ByteCNN,image

def train(manifest,output,epochs=10):
    m=json.loads(Path(manifest).read_text())
    if m.get('representation')!='original_bytes' or m.get('task') not in ('binary_detection','family_classification'):
        raise ValueError('Declare task and permitted original-byte provenance')
    random.seed(17);torch.manual_seed(17)
    model=ByteCNN(len(m['classes']));opt=torch.optim.Adam(model.parameters(),lr=.001)
    rows=m['samples'];train=[r for r in rows if r['split']=='train'];validation=[r for r in rows if r['split']=='validation']
    if not train or not validation: raise ValueError('Training and validation required')
    best=float('inf');out=Path(output);out.mkdir(parents=True,exist_ok=True)
    for epoch in range(epochs):
        model.train()
        for r in train:
            x=image(Path(r['path']).read_bytes()).unsqueeze(0);y=torch.tensor([r['label']]);opt.zero_grad();loss=torch.nn.functional.cross_entropy(model(x),y);loss.backward();opt.step()
        model.eval()
        with torch.no_grad(): val=sum(torch.nn.functional.cross_entropy(model(image(Path(r['path']).read_bytes()).unsqueeze(0)),torch.tensor([r['label']])).item() for r in validation)/len(validation)
        if val<best: best=val;torch.save(model.state_dict(),out/'cnn.pt')
    (out/'manifest.json').write_text(json.dumps({'task':m['task'],'classes':m['classes'],'validation_loss':best,'seed':17,'status':'experimental; not release authority'}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');a=p.parse_args();train(a.manifest,a.output)
