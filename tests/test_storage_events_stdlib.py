import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/api'))
from prooflane.storage_events import notifications

class StorageNotifications(unittest.TestCase):
    def record(self):return {'eventSource':'aws:s3','eventName':'ObjectCreated:Put','s3':{'bucket':{'name':'private'},'object':{'key':'tenant%2Ffile+name','versionId':'exact-version','sequencer':'1'}}}
    def test_decodes_and_deduplicates_exact_identity(self):
        body=json.dumps({'Records':[self.record()]});a=notifications(body,'private')[0]
        self.assertEqual(a['key'],'tenant/file name')
        self.assertEqual(a,notifications(body,'private')[0])
    def test_versions_have_separate_receipts(self):
        a=self.record();b=self.record();b['s3']['object']['versionId']='other'
        rows=notifications(json.dumps({'Records':[a,b]}),'private');self.assertNotEqual(rows[0]['event_key'],rows[1]['event_key'])
    def test_missing_exact_version_rejected(self):
        for value in [None,'null','']:
            r=self.record();r['s3']['object']['versionId']=value
            with self.assertRaises(ValueError):notifications(json.dumps({'Records':[r]}),'private')
    def test_foreign_bucket_rejected(self):
        with self.assertRaises(ValueError):notifications(json.dumps({'Records':[self.record()]}),'foreign')
    def test_s3_destination_validation_message(self):
        self.assertEqual(notifications(json.dumps({'Event':'s3:TestEvent','Bucket':'private'}),'private'),[])
    def test_non_s3_event_rejected(self):
        r=self.record();r['eventSource']='untrusted'
        with self.assertRaises(ValueError):notifications(json.dumps({'Records':[r]}),'private')
    def test_empty_envelope_rejected(self):
        with self.assertRaises(ValueError):notifications('{}','private')
