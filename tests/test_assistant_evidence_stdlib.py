import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from prooflane.assistant_evidence import CitationValidationError, TOOL_NAME, explain, render_claims


EVENT = '12345678-1234-1234-1234-123456789abc'
OTHER = 'aaaaaaaa-1234-1234-1234-123456789abc'
EVIDENCE = [{'id': EVENT, 'kind': 'VERIFICATION_QUARANTINED', 'version': OTHER}]


def content(ids=None, text='Verification recorded quarantine.'):
    return json.dumps({'claims': [{'text': text, 'event_ids': [EVENT] if ids is None else ids}]})


def response(text):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)],
                           usage=SimpleNamespace(input_tokens=13, output_tokens=8))


class AuthorizedClaims(unittest.TestCase):
    def test_server_formats_canonical_authorized_citations(self):
        result = render_claims(content([EVENT.upper(), EVENT]), EVIDENCE)
        self.assertEqual(result, 'Verification recorded quarantine. [' + EVENT + ']')

    def test_accepts_fenced_json(self):
        self.assertIn('[' + EVENT + ']', render_claims('```json\n' + content() + '\n```', EVIDENCE))

    def test_rejects_unknown_and_version_ids(self):
        for ids in ([OTHER], ['not-an-id'], [EVENT, OTHER], [None], []):
            with self.subTest(ids=ids), self.assertRaises(CitationValidationError):
                render_claims(content(ids), EVIDENCE)

    def test_cannot_embed_unvalidated_citations_in_text(self):
        for text in ('False claim [' + OTHER + ']', 'Even a valid reference [' + EVENT + ']', '[event]'):
            with self.subTest(text=text), self.assertRaises(CitationValidationError):
                render_claims(content(text=text), EVIDENCE)

    def test_rejects_missing_or_malformed_claims(self):
        for value in ('Plain prose', '[]', '{}', '{"claims":[]}', '{"claims":[null]}',
                      '{"claims":[{"text":"Uncited claim"}]}', '{"claims":[],"answer":"uncited"}'):
            with self.subTest(value=value), self.assertRaises(CitationValidationError):
                render_claims(value, EVIDENCE)

    def test_rejects_excessive_output(self):
        with self.assertRaises(CitationValidationError):
            render_claims(content(text='a' * 1601), EVIDENCE)
        with self.assertRaises(CitationValidationError):
            render_claims('a' * 16001, EVIDENCE)
        with self.assertRaises(CitationValidationError):
            render_claims(json.dumps({'claims': [{'text': 'x', 'event_ids': [EVENT]}] * 4}), EVIDENCE)

    def test_no_repair_when_first_response_is_valid(self):
        client = Mock(); client.messages.create.return_value = response(content())
        usage = {}
        self.assertIn('[' + EVENT + ']', explain(client, 'configured-model', 'Why?', EVIDENCE, usage))
        self.assertEqual(client.messages.create.call_count, 1)
        self.assertEqual(usage, {'input_tokens': 13, 'output_tokens': 8})

    def test_tool_output_is_only_formatted_never_executed(self):
        client = Mock()
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='Uncited prefix must never be exposed'),
                SimpleNamespace(type='tool_use', name=TOOL_NAME, input=json.loads(content()))],
            usage=SimpleNamespace(input_tokens=13, output_tokens=8))
        result = explain(client, 'configured-model', 'Why?', EVIDENCE, {})
        self.assertNotIn('Uncited prefix', result)
        arguments = client.messages.create.call_args.kwargs
        self.assertEqual(arguments['tool_choice'], {'type': 'tool', 'name': TOOL_NAME})
        ids = arguments['tools'][0]['input_schema']['properties']['claims']['items']['properties']['event_ids']['items']['enum']
        self.assertEqual(ids, [EVENT])

    def test_unexpected_tool_fails_closed(self):
        client = Mock()
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='tool_use', name='approve_file', input=json.loads(content()))],
            usage=SimpleNamespace(input_tokens=13, output_tokens=8))
        with self.assertRaises(CitationValidationError):
            explain(client, 'configured-model', 'Why?', EVIDENCE, {})
        self.assertEqual(client.messages.create.call_count, 2)

    def test_one_repair_accounts_for_both_calls(self):
        client = Mock(); client.messages.create.side_effect = [response(content([OTHER])), response(content())]
        usage = {}
        result = explain(client, 'configured-model', 'Why?', EVIDENCE, usage)
        self.assertIn('[' + EVENT + ']', result); self.assertNotIn('[' + OTHER + ']', result)
        self.assertEqual(client.messages.create.call_count, 2)
        self.assertEqual(usage, {'input_tokens': 26, 'output_tokens': 16})
        # Only the original authorized evidence is reused; rejected output isn't echoed.
        calls = client.messages.create.call_args_list
        self.assertEqual(calls[0].kwargs['messages'], calls[1].kwargs['messages'])

    def test_two_invalid_outputs_fail_closed_with_actual_usage(self):
        client = Mock(); client.messages.create.return_value = response(content([OTHER]))
        usage = {}
        with self.assertRaises(CitationValidationError):
            explain(client, 'configured-model', 'Why?', EVIDENCE, usage)
        self.assertEqual(client.messages.create.call_count, 2)
        self.assertEqual(usage, {'input_tokens': 26, 'output_tokens': 16})

    def test_transport_failure_retains_prior_token_usage(self):
        client = Mock(); client.messages.create.side_effect = [response('Invalid first output'), RuntimeError('Provider failed')]
        usage = {}
        with self.assertRaises(RuntimeError):
            explain(client, 'configured-model', 'Why?', EVIDENCE, usage)
        self.assertEqual(usage, {'input_tokens': 13, 'output_tokens': 8})


if __name__ == '__main__':
    unittest.main()
