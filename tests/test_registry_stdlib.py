import json
from pathlib import Path
import tempfile
import unittest
from ml.registry import manifest,status,sha256,version
from ml.context import INPUT_SCHEMA,MAX_EVENTS
from ml.data import FEATURES,HORIZON

class Registry(unittest.TestCase):
    def test_missing_checkpoint_unavailable(self):
        with tempfile.TemporaryDirectory() as d:self.assertFalse(status(d,'lightgbm')['available'])
    def test_manifest_without_weights_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'manifest.json').write_text('{}');self.assertFalse(status(d,'lightgbm')['available'])
    def test_metadata_integrity_detects_modified_bytes(self):
        # Byte fixtures only test integrity, never predict or claim trained models.
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for name in ['head-0.txt','head-1.txt']:(p/name).write_text('checkpoint integrity fixture')
            checkpoints={name:sha256(p/name) for name in ['head-0.txt','head-1.txt']}
            m={'method':'lightgbm','input_schema':INPUT_SCHEMA,'max_context_events':MAX_EVENTS,'features':FEATURES,'horizon':HORIZON,'checkpoints':checkpoints,'model_version':version('lightgbm',checkpoints)}
            (p/'manifest.json').write_text(json.dumps(m));self.assertEqual(manifest(p,'lightgbm')['model_version'],m['model_version'])
            (p/'head-0.txt').write_text('changed')
            with self.assertRaises(ValueError):manifest(p,'lightgbm')
    def test_model_identity_depends_on_weights(self):self.assertNotEqual(version('tgn',{'weights.pt':'a'}),version('tgn',{'weights.pt':'b'}))
