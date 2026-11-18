import copy
import unittest

from scripts.live_assistant_smoke import validate_answer, validate_no_evidence


class AssistantSmokeValidation(unittest.TestCase):
    def setUp(self):
        self.event = '12345678-1234-1234-1234-123456789abc'
        self.response = {'status': 'answered', 'events': [{'id': self.event, 'version': 'v'}],
                         'answer': f'Recorded quarantine [{self.event}].',
                         'usage': {'input_tokens': 12, 'output_tokens': 7}}

    def test_authorized_answer(self):
        validate_answer(self.response, {self.event}, 'v')

    def test_rejects_fallback_or_fabricated_citations(self):
        for key, value in [('status', 'evidence_only'), ('answer', '[aaaaaaaa-1234-1234-1234-123456789abc]'), ('answer', 'No citations')]:
            response = copy.deepcopy(self.response); response[key] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_answer(response, {self.event}, 'v')

    def test_rejects_unknown_event_or_wrong_version(self):
        with self.assertRaises(ValueError): validate_answer(self.response, set(), 'v')
        with self.assertRaises(ValueError): validate_answer(self.response, {self.event}, 'other')

    def test_rejects_missing_actual_token_counts(self):
        for usage in ({}, {'input_tokens': True, 'output_tokens': 7}, {'input_tokens': 12, 'output_tokens': 0}):
            response = copy.deepcopy(self.response); response['usage'] = usage
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                validate_answer(response, {self.event}, 'v')

    def test_inaccessible_evidence_never_calls_provider(self):
        validate_no_evidence({'status': 'evidence_only', 'events': [], 'usage': {}})
        with self.assertRaises(ValueError): validate_no_evidence(self.response)


if __name__ == '__main__':
    unittest.main()
