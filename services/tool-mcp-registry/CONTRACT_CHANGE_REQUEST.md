# Proposed Registry -> Builder v0 contract change

**Status: PROPOSED; owner/integration approval pending.** Neither shared contracts nor agent-04 files have been changed.

## Verified mismatches (agent/04-agent-engine/agent_builder/core.py)

1. Builder `ToolManifest.approved` defaults to `false`; existing Registry `/manifests` omits this flag. A direct parse denies all otherwise approved operations.
2. Builder only accepts risk `low/medium/high` whereas Registry also has `CRITICAL`; it must not silently downgrade payment risk.
3. Builder `ToolBinding` has no `operation`, but the Registry's immutable coordinate is `(tenant, tool_id, version, operation)`. Multi-operation tools cannot be pinned uniquely in AgentSpec.
4. Builder's in-process exact set-cover rejects catalogues above 18 candidates, whereas Registry handles up to 256 bounded candidates. Duplicated optimizers can produce different selections.
5. Builder is not yet an HTTP consumer of the Registry's selected bindings; production integration and runtime revalidation are untested.

## Temporary fail-closed projection in workstream 03

`GET /v0/registry/builder/manifests` returns only approved, caller-scoped, tenant-visible operations with `operation=execute` and risk below `CRITICAL`. Adds `approved=true`, converts risk and effects to lowercase and retains tool/version/digest. It does not grant credentials or run MCP. More than 18 eligible candidates yields typed `BUILDER_PORT_CAPACITY` rather than a silently truncated list. Foreign tenants and callers without tool-specific scopes receive no operations.

Example (digest shown as placeholder, not a real registered manifest):

```json
{
  "tool_id": "catalog.lookup", "version": "1.0.0",
  "manifest_digest": "sha256:<64 hex characters>",
  "capabilities": ["catalog_lookup"], "side_effects": ["read"],
  "required_scopes": ["catalog:read"], "tenant_availability": ["tenant-a"],
  "input_schema_ref": "artifact://schemas/lookup-input",
  "output_schema_ref": "artifact://schemas/lookup-output",
  "risk_level": "low", "approved": true, "transport": "MCP"
}
```

## Proposed final integration contract

Builder should request **one** authenticated Registry `POST /v0/registry/select` per READY snapshot, with tenant, approved task effects/risk, capability requirements, version/schema pins, registry revision and correlation. The immutable AgentSpec binding needs `tool_id`, `operation`, `version`, `manifest_digest`, `granted_scopes`, `covered_capabilities`, and explicit side-effect evidence. Runtime must revalidate pinned approval and permissions on every operation. Any changes to Builder/AgentSpec/Runtime need coordinated agent-04 owner review, not unilateral changes by agent-03.

**Required evidence:** cross-language JSON decoding tests with live Builder port, wrong-tenant/denied-payment/revocation tests, version pinning, Maven MVC tests, and ADR-0002 ratification. Until then the projection is experimental and not evidence of full integration.
