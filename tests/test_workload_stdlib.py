import bisect
import unittest
from benchmarks.workload import build
from ml.context import validate_context

class Workload(unittest.TestCase):
    def test_causal_context_and_nonnegative_targets(self):
        rows=build(seed=3,files=5,jobs_per_family=12)
        self.assertEqual(len(rows),72)
        for r in rows:
            validate_context(r['context'],r['time']);self.assertGreaterEqual(r['y'][0],0);self.assertGreaterEqual(r['y'][1],0)
            self.assertLess(r['history_until'],r['time'])
            self.assertGreaterEqual(r['target_end'],r['time']+300)
    def test_initial_predictions_have_no_unobserved_labels(self):
        rows=build(seed=17,files=1,jobs_per_family=3)
        self.assertEqual(rows[0]['x'][3],0)
        self.assertEqual(rows[0]['x'][4],0)
        # Only upload/creation relationships, never the current future scan.
        self.assertTrue(all(e['time']<rows[0]['time'] for e in rows[0]['context']))
    def test_seed_reproducibility(self):self.assertEqual(build(5,3,3),build(5,3,3))
    def test_deadlines_are_variable_for_edf_comparison(self):
        rows=build(17,3,8)
        self.assertGreater(len({round(r['deadline']-r['time']) for r in rows}),1)
