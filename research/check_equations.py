"""Compare mathematical expectations with the project's pure decision functions."""
import csv
import json
from itertools import product
from pathlib import Path
from gateway.security import ReleaseFacts, release_denial
from gateway.scheduling import Candidate, rank

out = Path(__file__).resolve().parent / "gateway"
fields = ["authorized","current","approved","clean","bound","policy","integrity","fresh"]
with (out / "predicate.csv").open("w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(fields + ["expected","observed","reason"])
    for bits in product((0,1),repeat=len(fields)):
        a,c,s,k,b,p,i,fresh = bits
        facts = ReleaseFacts(a,c,"APPROVED" if s else "PENDING",k,b,p,i,101 if fresh else 100)
        reason = release_denial(facts,at=100)
        expected, observed = all(bits), reason is None
        assert observed == expected
        writer.writerow([*bits,int(expected),int(observed),reason or "allow"])
jobs = [Candidate("A","office",980,1200,1), Candidate("B","office",981,1150,1)]
predictions = {"A":(2,7), "B":(4,3)}
cases = {}
for strategy in ("edf","lightgbm","tgn"):
    cases[strategy] = [j.id for j in rank(jobs,strategy,1000,predictions)]
assert cases == {"edf":["B","A"],"lightgbm":["A","B"],"tgn":["A","B"]}
jobs[1].deadline = 1001
cases["urgent_override"] = [j.id for j in rank(jobs,"tgn",1000,predictions)]
assert cases["urgent_override"] == ["B","A"]
(out/"ranking-example.json").write_text(json.dumps(cases,indent=2))
