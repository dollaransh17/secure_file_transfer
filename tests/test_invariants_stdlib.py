"""Runnable without third-party packages: python -m unittest discover -s tests."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/api'))
from prooflane.security import ReleaseFacts,release_denial
from prooflane.scheduling import Candidate,rank
from benchmarks.oracle import Oracle
from benchmarks.run import conformance
from ml.data import split,load
from dataclasses import replace
class Safety(unittest.TestCase):
    def setUp(self): self.good=ReleaseFacts(True,True,'APPROVED',True,True,True,True,100)
    def test_release(self): self.assertIsNone(release_denial(self.good,10))
    def test_each_negative_condition(self):
        for field,value in [('authorized',False),('target_matches',False),('status','PENDING'),('scan_clean',False),('scan_bound',False),('policy_matches',False),('integrity_matches',False),('evidence_expires',1)]:
            with self.subTest(field=field): self.assertIsNotNone(release_denial(replace(self.good,**{field:value}),10))
    def test_late_v1_cannot_approve_v2(self):
        self.assertIsNotNone(release_denial(replace(self.good,scan_bound=False),10))
    def test_independent_scenarios(self):
        for r in conformance():
            with self.subTest(scenario=r['scenario']): self.assertTrue(r['pass'])
    def test_oracle_revocation(self):
        o=Oracle();self.assertTrue(o.permits(1,10));o.permission=False;self.assertFalse(o.permits(1,10))
    def test_deadline_overrides_prediction(self):
        jobs=[Candidate('urgent','a',99,100,1),Candidate('popular','a',99,1000,1)]
        self.assertEqual(rank(jobs,'tgn',100,{'urgent':(100,0),'popular':(.1,1000)})[0].id,'urgent')
    def test_starvation(self):
        self.assertEqual(rank([Candidate('old','a',0,1000,1),Candidate('new','a',199,900,1)],'edf',200)[0].id,'old')
    def test_fifo_and_edf(self):
        jobs=[Candidate('a','a',1,1000,1),Candidate('b','a',2,900,1)]
        self.assertEqual(rank(jobs,'fifo',3)[0].id,'a');self.assertEqual(rank(jobs,'edf',3)[0].id,'b')
    def test_temporal_split_purges_horizon(self):
        rows=[{'time':i*20} for i in range(200)];a,b,c=split(rows)
        self.assertLess(a[-1]['time']+300,b[0]['time']);self.assertLess(b[-1]['time']+300,c[0]['time'])
    def test_future_feature_rejected(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'rows';p.write_text(json.dumps({'time':1,'history_until':2,'x':[0]*8}))
            with self.assertRaises(ValueError):load(p)
if __name__=='__main__':unittest.main()
