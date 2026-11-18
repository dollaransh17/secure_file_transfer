import copy
import unittest

from scripts.live_ml_smoke import validate_decision


class ModelDecisionChecks(unittest.TestCase):
    def setUp(self):
        self.job = {'id': 'j', 'version_id': 'v', 'status': 'COMPLETE'}
        self.decision = {'job_id': 'j', 'strategy': 'lightgbm', 'inputs': {
            'model_version': 'trained-id', 'fallback': None, 'prediction': [1.5, 2.0],
            'feature_schema': 2, 'features': [0] * 8}}

    def check(self, decision):
        return validate_decision(self.job, decision, 'lightgbm', 'trained-id')

    def test_completed_model_decision(self):
        self.assertEqual(self.check(self.decision)['version_id'], 'v')

    def test_rejects_fallback_and_mismatched_identity(self):
        for key, value in [('fallback', 'ImportError'), ('model_version', 'other')]:
            bad = copy.deepcopy(self.decision); bad['inputs'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.check(bad)
        bad = copy.deepcopy(self.decision); bad['strategy'] = 'edf'
        with self.assertRaises(ValueError): self.check(bad)

    def test_rejects_missing_or_invalid_predictions(self):
        for prediction in (None, [], [1], [1, float('nan')], [float('inf'), 1], [-1, 2], [True, 1], ['1', 2]):
            bad = copy.deepcopy(self.decision); bad['inputs']['prediction'] = prediction
            with self.subTest(prediction=prediction), self.assertRaises(ValueError): self.check(bad)

    def test_rejects_unbound_or_unfinished_job(self):
        bad = copy.deepcopy(self.decision); bad['job_id'] = 'other'
        with self.assertRaises(ValueError): self.check(bad)
        self.job['status'] = 'PENDING'
        with self.assertRaises(ValueError): self.check(self.decision)


if __name__ == '__main__':
    unittest.main()
