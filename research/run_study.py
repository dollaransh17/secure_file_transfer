"""Reproduce the offline file-format experiment using benign generated files."""
import csv
import hashlib
import json
import platform
import random
import statistics
import time
from pathlib import Path

import torch
from torch import nn
from ml.cnn.model import ByteCNN, image
from ml.cnn.infer import infer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cnn-results"
CLASSES = ["txt", "csv", "json", "pdf", "png"]
SEED = 17
EPOCHS = 10
BATCH = 8
NAMES = ["ByteCNN 2D", "Sequence CNN 1D", "Separable CNN 2D"]


def make_model(name):
    if name == NAMES[0]:
        return ByteCNN(len(CLASSES))
    if name == NAMES[1]:
        return nn.Sequential(nn.Flatten(start_dim=2), nn.Conv1d(1, 16, 16, stride=8), nn.ReLU(),
                             nn.MaxPool1d(2), nn.Conv1d(16, 32, 5, padding=2), nn.ReLU(),
                             nn.AdaptiveMaxPool1d(16), nn.Flatten(), nn.Linear(512, len(CLASSES)))
    return nn.Sequential(nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Conv2d(16, 16, 3, padding=1, groups=16), nn.Conv2d(16, 32, 1),
                         nn.ReLU(), nn.AdaptiveAvgPool2d((4, 4)), nn.Flatten(), nn.Linear(512, len(CLASSES)))


def score(truth, pred):
    matrix = [[0 for _ in CLASSES] for _ in CLASSES]
    for a, b in zip(truth, pred):
        matrix[a][b] += 1
    f1 = []
    for i, row in enumerate(matrix):
        denominator = sum(row) + sum(r[i] for r in matrix)
        f1.append(2 * row[i] / denominator if denominator else 0.)
    return dict(correct=sum(matrix[i][i] for i in range(len(CLASSES))), n=len(truth),
                macro_f1=statistics.mean(f1), confusion=matrix)


def write_csv(filename, rows):
    with (OUT / filename).open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    rows, seen = [], set()
    rng = random.Random(SEED)
    for label in CLASSES:
        files = sorted((ROOT / "fixtures").glob("*." + label))
        assert len(files) == 40
        rng.shuffle(files)
        for i, path in enumerate(files):
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            assert digest not in seen
            seen.add(digest)
            rows.append(dict(file=path.name, label=label, bytes=len(data), sha256=digest,
                             split="train" if i < 24 else "validation" if i < 32 else "test"))
    write_csv("splits.csv", rows)
    x = torch.stack([image((ROOT / "fixtures" / r["file"]).read_bytes()) for r in rows])
    y = torch.tensor([CLASSES.index(r["label"]) for r in rows])
    ix = {s: torch.tensor([i for i, r in enumerate(rows) if r["split"] == s]) for s in ("train","validation","test")}
    test_ids = ix["test"].tolist()
    truth = y[test_ids].tolist()
    med = [statistics.median(r["bytes"] for r in rows if r["split"] == "train" and r["label"] == c) for c in CLASSES]
    pred = [min(range(len(CLASSES)), key=lambda c: abs(rows[i]["bytes"] - med[c])) for i in test_ids]
    results = {"Length baseline":score(truth, pred)}
    logs, tests = [], []
    for i, label in zip(test_ids, pred):
        tests.append(dict(model="Length baseline",file=rows[i]["file"],actual=rows[i]["label"],predicted=CLASSES[label]))
    loss_fn = nn.CrossEntropyLoss()
    for name in NAMES:
        torch.manual_seed(SEED)
        model = make_model(name)
        optimizer = torch.optim.Adam(model.parameters(), lr=.003)
        order = torch.Generator().manual_seed(SEED)
        best = float("inf")
        for epoch in range(1, EPOCHS+1):
            model.train()
            for idx in ix["train"][torch.randperm(len(ix["train"]),generator=order)].split(BATCH):
                optimizer.zero_grad()
                loss_fn(model(x[idx]), y[idx]).backward()
                optimizer.step()
            model.eval()
            with torch.inference_mode():
                logits = torch.cat([model(x[idx]) for idx in ix["validation"].split(BATCH)])
                val = loss_fn(logits,y[ix["validation"]]).item()
            logs.append(dict(model=name,epoch=epoch,validation_loss=val))
            if val < best:
                best, best_epoch = val, epoch
                weights = {k:v.detach().clone() for k,v in model.state_dict().items()}
        model.load_state_dict(weights)
        with torch.inference_mode():
            for _ in range(6):
                model(x[test_ids[:1]])
            preds, latency = [], []
            for i in test_ids:
                tensor = x[i:i+1]
                tic = time.perf_counter()
                out = model(tensor)
                latency.append((time.perf_counter()-tic)*1000)
                preds.append(out.argmax(1).item())
        for i,label in zip(test_ids,preds):
            tests.append(dict(model=name,file=rows[i]["file"],actual=rows[i]["label"],predicted=CLASSES[label]))
        results[name] = dict(**score(truth,preds),parameters=sum(p.numel() for p in model.parameters()),
                             epoch=best_epoch,val_loss=best,median_ms=statistics.median(latency))
        if name == NAMES[0]:
            directory = OUT / "bytecnn-format"
            directory.mkdir(exist_ok=True)
            torch.save(weights,directory/"cnn.pt")
            (directory/"manifest.json").write_text(json.dumps({"task":"benign_fixture_format","classes":CLASSES}))
            for i, label in zip(test_ids,preds):
                prediction = infer((ROOT/"fixtures"/rows[i]["file"]).read_bytes(), directory)
                assert prediction["probabilities"].index(max(prediction["probabilities"])) == label
        print(name,results[name],flush=True)
    write_csv("validation.csv",logs)
    write_csv("predictions.csv",tests)
    (OUT/"results.json").write_text(json.dumps(dict(seed=SEED,epochs=EPOCHS,batch=BATCH,lr=.003,
        torch=str(torch.__version__),python=platform.python_version(),machine=platform.machine(),os=platform.platform(),classes=CLASSES,results=results),indent=2))


if __name__ == "__main__":
    main()
