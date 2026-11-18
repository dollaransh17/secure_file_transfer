import json
from pathlib import Path
import torch
from .model import ByteCNN,image

def infer(data,directory):
    d=Path(directory);manifest=json.loads((d/'manifest.json').read_text())
    model=ByteCNN(len(manifest['classes']));model.load_state_dict(torch.load(d/'cnn.pt',map_location='cpu',weights_only=True));model.eval()
    with torch.no_grad():probabilities=model(image(data).unsqueeze(0)).softmax(-1)[0].tolist()
    return {'task':manifest['task'],'classes':manifest['classes'],'probabilities':probabilities,'experimental':True,'release_authority':False}
