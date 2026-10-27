import pytest
from agent_runtime import MCPBackend, MCPBinding, RuntimeDenied


class FakeResponse:
    def __init__(self, payload=None, error=False):
        self.structuredContent,self.isError=payload,error

class FakeClient:
    def __init__(self): self.calls=[]
    async def call_tool(self, *,name,arguments):
        self.calls.append((name,arguments))
        return FakeResponse({'rows':[{'sku':'BOLT-1','usd':12}]})

@pytest.mark.asyncio
async def test_authorized_mcp_mapping_and_cross_tenant_denial():
    client=FakeClient()
    binding=MCPBinding(tenant_id='buyer',tool_id='catalog.lookup',
                       remote_tool_name='catalog_search',client_alias='approved')
    backend=MCPBackend(clients={'approved':client},bindings={'catalog.lookup':binding})
    with pytest.raises(RuntimeDenied,match='MCP_TOOL_DENIED'):
        await backend.call(tenant_id='seller',tool_id='catalog.lookup',
                           args={},idempotency_key='x')
    with pytest.raises(RuntimeDenied,match='MCP_TOOL_DENIED'):
        await backend.call(tenant_id='buyer',tool_id='unknown',args={},idempotency_key='x')
    found=await backend.call(tenant_id='buyer',tool_id='catalog.lookup',
                             args={'sku':'BOLT-1'},idempotency_key='x')
    assert found['rows'][0]['usd']==12
    assert client.calls==[('catalog_search',{'sku':'BOLT-1'})]

def test_unknown_mcp_host_fails_closed():
    with pytest.raises(RuntimeDenied,match='MCP_BINDING_DENIED'):
        MCPBackend(clients={},bindings={'tool':MCPBinding(
            tenant_id='buyer',tool_id='tool',remote_tool_name='search',
            client_alias='unknown')})

@pytest.mark.asyncio
async def test_mcp_remote_error_and_unstructured_reply_denied():
    binding=MCPBinding(tenant_id='buyer',tool_id='tool',
                       remote_tool_name='tool',client_alias='trusted')
    class Bad:
        async def call_tool(self,**kwargs): return FakeResponse(error=True)
    backend=MCPBackend(clients={'trusted':Bad()},bindings={'tool':binding})
    with pytest.raises(RuntimeDenied,match='MCP_TOOL_ERROR'):
        await backend.call(tenant_id='buyer',tool_id='tool',args={},idempotency_key='x')
    class PlainText:
        async def call_tool(self,**kwargs): return FakeResponse()
    backend=MCPBackend(clients={'trusted':PlainText()},bindings={'tool':binding})
    with pytest.raises(RuntimeDenied,match='MCP_UNSTRUCTURED_RESULT'):
        await backend.call(tenant_id='buyer',tool_id='tool',args={},idempotency_key='x')

def test_effectful_mcp_is_denied_until_remote_idempotency_review():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MCPBinding(tenant_id='buyer',tool_id='payment',remote_tool_name='send_payment',
                   client_alias='trusted',allowed_effect='payment')
