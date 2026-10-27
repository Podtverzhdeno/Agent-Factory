"""Fail-closed version-pinned tool/MCP gateway with local JSON Schema validation."""
from __future__ import annotations
from typing import Any, Mapping
from jsonschema import Draft202012Validator, SchemaError, ValidationError
from pydantic import BaseModel, ConfigDict, Field
from agent_builder import AgentSpec, ToolBinding
from .core import RuntimeDenied, ToolGateway

class ToolPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    tenant_id: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    manifest_digest: str = Field(min_length=1)
    scopes: frozenset[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    effect_mode: str = 'read'

def _reject_remote_or_dynamic_refs(schema: object) -> None:
    if isinstance(schema, dict):
        if '$ref' in schema or '$dynamicRef' in schema:
            raise RuntimeDenied('UNTRUSTED_SCHEMA_REFERENCE')
        for value in schema.values():
            _reject_remote_or_dynamic_refs(value)
    elif isinstance(schema, list):
        for value in schema:
            _reject_remote_or_dynamic_refs(value)

class VerifiedToolGateway(ToolGateway):
    """Registry-issued policies must be trusted; model text never grants permission."""
    verified = True

    def __init__(self, tools, ledger, *, policies: Mapping[str, ToolPolicy],
                 timeout_seconds: float = 15.0):
        super().__init__(tools, ledger, timeout_seconds=timeout_seconds)
        self.policies = dict(policies)
        for policy in self.policies.values():
            _reject_remote_or_dynamic_refs(policy.input_schema)
            _reject_remote_or_dynamic_refs(policy.output_schema)
            try:
                Draft202012Validator.check_schema(policy.input_schema)
                Draft202012Validator.check_schema(policy.output_schema)
            except SchemaError as exc:
                raise RuntimeDenied('INVALID_TOOL_SCHEMA') from exc

    async def execute(self, spec: AgentSpec, binding: ToolBinding, *, args: dict,
                      run_id: str, step: int) -> tuple[dict, str]:
        policy = self.policies.get(binding.tool_id)
        if policy is None or binding not in spec.selected_tools:
            raise RuntimeDenied('TOOL_DENIED')
        if (policy.tenant_id != spec.tenant_id or policy.tool_id != binding.tool_id
            or policy.version != binding.version or policy.manifest_digest != binding.digest
            or not set(binding.granted_scopes) <= policy.scopes):
            raise RuntimeDenied('TOOL_PIN_OR_SCOPE_DENIED')
        if set(binding.side_effects) != {policy.effect_mode}:
            raise RuntimeDenied('TOOL_EFFECT_MISMATCH')
        try:
            Draft202012Validator(policy.input_schema).validate(args)
        except ValidationError as exc:
            raise RuntimeDenied('INVALID_TOOL_INPUT') from exc

        class ValidatingPort:
            def __init__(self, inner):
                self.inner = inner
            async def call(self, **kwargs):
                output = await self.inner.call(**kwargs)
                try:
                    Draft202012Validator(policy.output_schema).validate(output)
                except ValidationError as exc:
                    raise RuntimeDenied('INVALID_TOOL_OUTPUT') from exc
                return output

        # Validate external output BEFORE the effect reservation is confirmed.
        gateway = ToolGateway(ValidatingPort(self.tools), self.ledger,
                              timeout_seconds=self.timeout_seconds)
        return await gateway.execute(spec, binding, args=args, run_id=run_id, step=step)
