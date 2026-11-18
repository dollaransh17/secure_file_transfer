"""Live-check diagnostics with explicit HTTP transport doubles, no cloud calls."""
import httpx
import pytest
from scripts.live_smoke import API, eicar_pattern, verify_evidence


def client(handler):
    api = API(httpx, 'http://127.0.0.1:8001', 'http://localhost:5174')
    api.client.close()
    api.client = httpx.Client(base_url='http://127.0.0.1:8001', transport=httpx.MockTransport(handler))
    return api


def test_upload_uses_its_own_bounded_budget_and_returns_confirmed_version():
    seen = []

    def handle(request):
        seen.append(request.extensions['timeout'])
        return httpx.Response(200, json={'id': 'confirmed-version'})

    api = client(handle)
    try:
        assert api.upload('fixture.txt', b'harmless') == {'id': 'confirmed-version'}
        assert seen == [{'connect': 30, 'read': 90, 'write': 30, 'pool': 30}]
    finally:
        api.client.close()


def test_upload_timeout_is_unconfirmed_not_retried_and_does_not_echo_transport_secrets():
    requests = []

    def handle(request):
        requests.append(request)
        raise httpx.ReadTimeout('sensitive-transport-details', request=request)

    api = client(handle)
    try:
        with pytest.raises(RuntimeError) as caught:
            api.upload('fixture.txt', b'harmless')
        assert len(requests) == 1
        assert 'POST /api/files: ReadTimeout' in str(caught.value)
        assert 'outcome is unconfirmed' in str(caught.value)
        assert 'sensitive-transport-details' not in str(caught.value)
    finally:
        api.client.close()


@pytest.mark.parametrize('field,value', [('digest', 'wrong-digest'), ('object_version', 'wrong-version'), ('result', 'CLEAN')])
def test_quarantine_evidence_must_match_exact_infected_version(field, value):
    version = {'id': 'version-id', 'digest': 'expected-digest', 'object_version': 'expected-object-version'}
    scan = {**version, 'version_id': version['id'], 'result': 'INFECTED', 'created': 1, 'engine': 'ClamAV actual engine'}
    scan[field] = value
    with pytest.raises(RuntimeError, match='Scan evidence does not match'):
        verify_evidence({'scans': [scan], 'integrity': []}, version, 'INFECTED')


def test_live_av_fixture_remains_the_standard_68_byte_pattern():
    import hashlib
    assert len(eicar_pattern()) == 68
    assert hashlib.sha256(eicar_pattern()).hexdigest() == '275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f'
