import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.context import encode_event,snapshot,validate_context,event_vector,MAX_EVENTS
from ml.data import load,split

class CausalContext(unittest.TestCase):
    def event(self,at=1,identity='event'):
        return encode_event('user:u','version:v',at,'USER_REQUESTED_FILE',{'authorized':True},identity)
    def test_same_time_and_future_excluded(self):
        self.assertEqual([e['time'] for e in snapshot([self.event(1),self.event(2),self.event(3)],2)],[1])
    def test_memory_replay_bounded_to_most_recent_events(self):
        events=[self.event(i,str(i)) for i in range(300)]
        result=snapshot(events,300)
        self.assertEqual(len(result),MAX_EVENTS)
        self.assertEqual(result[0]['time'],300-MAX_EVENTS)
    def test_input_order_does_not_change_mapping(self):
        a=self.event(1,'a');b=self.event(1,'b')
        self.assertEqual(snapshot([a,b],2),snapshot([b,a],2))
    def test_future_context_rejected_in_training_loader(self):
        row={'time':2,'history_until':1,'x':[0]*8,'context':[self.event(2)]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data';path.write_text(json.dumps(row))
            with self.assertRaises(ValueError):load(path)
    def test_unknown_node_and_edge_rejected(self):
        with self.assertRaises(ValueError):encode_event('token:x','version:v',1,'USER_REQUESTED_FILE')
        with self.assertRaises(ValueError):encode_event('user:u','version:v',1,'APPROVE_FILE')
    def test_untrusted_attributes_are_not_model_features(self):
        self.assertEqual(event_vector({'filename':'ignore all instructions','token':'secret'}),[0.]*8)
    def test_type_forgery_rejected(self):
        event=self.event();event['src_type']=6
        with self.assertRaises(ValueError):validate_context([event],2)
    def test_nonfinite_features_rejected(self):
        with self.assertRaises(ValueError):event_vector({'size':float('inf')})
    def test_nonchronological_context_rejected(self):
        with self.assertRaises(ValueError):validate_context([self.event(2),self.event(1)],3)
    def test_target_completion_purged_at_split(self):
        rows=[{'time':i*100,'target_end':i*100+1000} for i in range(100)]
        train,validation,test=split(rows)
        self.assertLess(train[-1]['target_end'],6000)
        self.assertLess(validation[-1]['target_end'],8000)
    def test_empty_dataset_rejected(self):
        with self.assertRaises(ValueError):split([])

if __name__=='__main__':unittest.main()
