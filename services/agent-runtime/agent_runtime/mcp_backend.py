"""Approved MCP client adapter. MCP is transport, NOT authority."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .core import RuntimeDenied


class MCPClientPort(Protocol):
    async def call_tool(self, *, name: str, arguments: dict[str, Any]) -> Any: ...

class MCPBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    tenant_id: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    remote_tool_name: str = Field(min_length=1)
    client_alias: str = Field(min_length=1)
    allowed_effect: Literal['read'] = 'read'

class MCPBackend:
    """Call only through VerifiedToolGateway with pinned Registry-issued grants.

    No dynamic host discovery, implicit MCP installation, or secret handling.
    An MCP tool returning text instead of structuredContent fails closed.
    """
    def __init__(self, *, clients: Mapping[str, MCPClientPort],
                 bindings: Mapping[str, MCPBinding]):
        self._clients = dict(clients)
        self._bindings = dict(bindings)
        for tool_id, binding in self._bindings.items():
            if tool_id != binding.tool_id or binding.client_alias not in self._clients:
                raise RuntimeDenied('MCP_BINDING_DENIED')

    async def call(self, *, tenant_id: str, tool_id: str, args: dict,
                   idempotency_key: str) -> dict:
        binding = self._bindings.get(tool_id)
        if binding is None or binding.tenant_id != tenant_id:
            raise RuntimeDenied('MCP_TOOL_DENIED')
        # Remote MCP side effects MUST have an independently reviewed
        # idempotency contract before use. This adapter is read-only in MVP.
        result = await self._clients[binding.client_alias].call_tool(
            name=binding.remote_tool_name, arguments=args)
        if getattr(result, 'isError', False) or getattr(result, 'is_error', False):
            raise RuntimeDenied('MCP_TOOL_ERROR')
        structured = getattr(result, 'structuredContent', None)
        if structured is None:
            structured = getattr(result, 'structured_content', None)
        if not isinstance(structured, dict):
            raise RuntimeDenied('MCP_UNSTRUCTURED_RESULT')
        return structured
