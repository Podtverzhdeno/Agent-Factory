import json
import httpx
import pytest
from agent_runtime import RuntimeDenied
from litellm_adapter import LiteLLMGateway

def gateway(handler, allowed=frozenset({'mock-model'})):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return LiteLLMGateway(base_url='http://127.0.0.1:9999', tenant_id='buyer',
                          allowed_routes=allowed, tenant_key_provider=lambda t: 'mock-injected-token',
                          http_client=client)

@pytest.mark.asyncio
async def test_proxy_mock_route_usage_and_trace():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={'choices': [{'message': {'content':
            json.dumps({'kind': 'final', 'text': 'Source: catalog'})}}], 'usage': {'cost': 0.01}})
    gw = gateway(handler)
    d = await gw.decide(route='mock-model', prompt='safe', history=[{'role':'user','content':'hi'}],
                        tool_ids=(), trace_id='trace-1')
    assert d.text == 'Source: catalog' and d.estimated_usd == .01
    assert calls[0].headers['X-Trace-ID'] == 'trace-1'
    assert calls[0].headers['Authorization'] == 'Bearer mock-injected-token'

@pytest.mark.asyncio
async def test_model_denial_and_proxy_unavailable():
    gw = gateway(lambda _: httpx.Response(503))
    with pytest.raises(RuntimeDenied, match='MODEL_DENIED'):
        await gw.decide(route='other', prompt='x', history=[], tool_ids=(), trace_id='t')
    with pytest.raises(RuntimeDenied, match='PROVIDER_UNAVAILABLE'):
        await gw.decide(route='mock-model', prompt='x', history=[], tool_ids=(), trace_id='t')

@pytest.mark.asyncio
async def test_proxy_missing_cost_denied():
    gw = gateway(lambda _: httpx.Response(200, json={'choices': [{'message':
        {'content': json.dumps({'kind': 'final', 'text': 'ok'})}}]}))
    with pytest.raises(RuntimeDenied, match='MISSING_PROXY_COST'):
        await gw.decide(route='mock-model', prompt='safe', history=[], tool_ids=(), trace_id='trace')
