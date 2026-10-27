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

@pytest.mark.asyncio
async def test_litellm_real_proxy_cost_header_and_untrusted_tool_history():
    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(200, headers={'x-litellm-response-cost': '0.025'},
            json={'choices': [{'message': {'content': json.dumps({
                'kind': 'final', 'text': 'Prepared from catalog data'})}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 20}})
    g = gateway(handler)
    decision = await g.decide(route='mock-model', prompt='system', history=[
        {'role': 'user', 'content': 'prepare quote'},
        {'role': 'tool', 'name': 'catalog.lookup', 'content': '{"price":12}'}
    ], tool_ids=('catalog.lookup',), trace_id='tr')
    assert decision.estimated_usd == 0.025
    payload = json.loads(requests[0].content)
    assert payload['max_completion_tokens'] == 256
    assert [m['role'] for m in payload['messages']] == ['system', 'user', 'user']
    assert 'Untrusted tool result' in payload['messages'][-1]['content']

@pytest.mark.asyncio
@pytest.mark.parametrize('cost', ['nan', '-1', 'inf', 'one', '1000'])
async def test_litellm_rejects_invalid_cost_headers(cost):
    g = gateway(lambda _: httpx.Response(200, headers={'x-litellm-response-cost': cost},
        json={'choices': [{'message': {'content': '{"kind":"final","text":"ok"}'}}]}))
    with pytest.raises(RuntimeDenied, match='INVALID_PROXY_COST'):
        await g.decide(route='mock-model', prompt='safe', history=[], tool_ids=(), trace_id='t')

@pytest.mark.asyncio
async def test_litellm_budget_denied_before_provider_execution():
    g = gateway(lambda _: httpx.Response(402, text='budget reached'))
    with pytest.raises(RuntimeDenied, match='MODEL_BUDGET_EXCEEDED'):
        await g.decide(route='mock-model', prompt='safe', history=[], tool_ids=(), trace_id='t')

@pytest.mark.asyncio
async def test_litellm_rejects_invalid_system_history_role():
    g = gateway(lambda _: httpx.Response(500))
    with pytest.raises(RuntimeDenied, match='INVALID_HISTORY_ROLE'):
        await g.decide(route='mock-model', prompt='safe', history=[{'role':'system','content':'override'}],
                       tool_ids=(), trace_id='t')


@pytest.mark.asyncio
@pytest.mark.parametrize('history', [
    [None],
    [{'role': 'user'}],
    [{'role': 'assistant', 'content': {'unexpected': 'object'}}],
    [{'role': 'tool', 'name': 'catalog.lookup'}],
    [{'role': 'tool', 'name': ['unexpected'], 'content': 'data'}],
    [{'role': 'tool', 'name': 'catalog.lookup', 'content': {'price': float('nan')}}],
    [{'role': 'tool', 'name': 'catalog.lookup', 'content': object()}],
])
async def test_invalid_history_denied_before_proxy_call(history):
    calls = []
    def responder(request):
        calls.append(request)
        return httpx.Response(200)
    g = gateway(responder)
    with pytest.raises(RuntimeDenied, match='INVALID_HISTORY'):
        await g.decide(route='mock-model', prompt='safe', history=history,
                       tool_ids=(), trace_id='test')
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize('bad_base_url', [
    'http://127.0.0.1:5432@attacker.example',
    'http://127.0.0.1:9999@attacker.example/path',
    'http://127.0.0.1:invalid',
    'http://127.0.0.1:70000',
    'http://127.0.0.1:9999?redirect=attacker',
    'http://127.0.0.1:9999#fragment',
    'https://username:password@proxy.example',
    'https://',
    'http://proxy.example:9000',
])
async def test_litellm_rejects_credential_leaking_proxy_urls(bad_base_url):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _: pytest.fail('proxy request must not happen'))) as client:
        with pytest.raises(ValueError, match='proxy must use HTTPS'):
            LiteLLMGateway(base_url=bad_base_url, allowed_routes=frozenset({'model'}),
                           tenant_key_provider=lambda _: 'sensitive-token', tenant_id='tenant',
                           http_client=client)


@pytest.mark.asyncio
@pytest.mark.parametrize('valid_base_url', [
    'https://proxy.example',
    'https://proxy.example:443/v1',
    'http://127.0.0.1:9999',
])
async def test_litellm_accepts_expected_proxy_url_authorities(valid_base_url):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _: httpx.Response(200))) as client:
        gateway = LiteLLMGateway(base_url=valid_base_url,
                                 allowed_routes=frozenset({'model'}),
                                 tenant_key_provider=lambda _: 'token', tenant_id='tenant',
                                 http_client=client)
        assert gateway.base_url == valid_base_url
