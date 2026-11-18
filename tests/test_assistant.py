"""Claude transport is mocked; account keys and real API charges are never used."""
import json
from test_api import isolated
from types import SimpleNamespace
from unittest.mock import Mock

def test_account_model_checked_without_pagination(isolated,monkeypatch):
    from test_api import register,uploaded
    from prooflane.config import settings
    from prooflane import assistant
    import anthropic
    client=Mock()
    def create(**kwargs):
        item=json.loads(kwargs['messages'][0]['content'])['evidence'][0]
        claims={'claims':[{'text':'This upload was quarantined pending verification.','event_ids':[item['id']]}]}
        return SimpleNamespace(content=[SimpleNamespace(type='tool_use',name='format_security_explanation',input=claims)],usage=SimpleNamespace(input_tokens=23,output_tokens=11))
    client.messages.create.side_effect=create
    monkeypatch.setattr(anthropic,'Anthropic',lambda **kwargs:client)
    monkeypatch.setattr(settings(),'anthropic_api_key','unit-test-placeholder')
    monkeypatch.setattr(settings(),'anthropic_model','configured-account-model')
    a,_=register();uploaded(a)
    response=a.post('/api/assistant',json={'question':'Why is this pending?'})
    assert response.status_code==200
    assert response.json()['status']=='answered'
    assert response.json()['usage']=={'input_tokens':23,'output_tokens':11}
    client.models.retrieve.assert_called_once_with('configured-account-model')
    client.models.list.assert_not_called()

def test_invalid_citations_fail_closed_and_record_token_usage(isolated,monkeypatch):
    from test_api import register,uploaded
    from prooflane.config import settings
    import anthropic
    client=Mock()
    invalid=json.dumps({'claims':[{'text':'Unsupported explanation.','event_ids':['aaaaaaaa-1234-1234-1234-123456789abc']}]})
    client.messages.create.return_value=SimpleNamespace(
        content=[SimpleNamespace(type='text',text=invalid)],
        usage=SimpleNamespace(input_tokens=13,output_tokens=8))
    monkeypatch.setattr(anthropic,'Anthropic',lambda **kwargs:client)
    monkeypatch.setattr(settings(),'anthropic_api_key','unit-test-placeholder')
    monkeypatch.setattr(settings(),'anthropic_model','configured-account-model')
    a,_=register();uploaded(a)
    result=a.post('/api/assistant',json={'question':'Why is this pending?'}).json()
    assert result['status']=='unavailable:CitationValidationError'
    assert 'Unsupported explanation' not in result['answer']
    assert result['usage']=={'input_tokens':26,'output_tokens':16}
    assert client.messages.create.call_count==2
