# Frozen proposed integration contracts v0 (read-only to coding agents)

**Status:** PROPOSED. Canonical behavior is in `openspec/changes/bootstrap-factory-mvp/**`; owner ADR-0002 still not ratified. Contract structs are illustrative transport-neutral JSON shapes, not already deployed endpoints. All messages/IDs must be scoped to `tenant_id`; APIs must authenticate/authorize requests. Version every operation and event schema. Never transmit uploaded binary files or raw secrets over Kafka.

## Shared identifiers & invariants

`tenant_id`, `task_id`, `task_snapshot_id`, `build_id`, `agent_id`, `agent_spec_version`, `evaluation_run_id`, `artifact_ref`, `trace_id`, `correlation_id`, `idempotency_key`.

Every cross-service command is idempotent per tenant + key, returns either a typed result or a verifiable BLOCKED/FAILED reason. Every asynchronous event carries `event_id`, `schema_version`, `occurred_at`, `tenant_id`, `correlation_id` and a relevant state/version reference. Kafka events report outcomes; Orchestrator explicitly initiates work.

## 1. Task Snapshot — owner: agent 02

```json
{
  "schema_version":"0.1","tenant_id":"tenant-a","task_id":"rfq-001",
  "task_snapshot_id":"snap-001","status":"READY",
  "objective":"produce a verified draft RFQ quotation",
  "input_contract_ref":"artifact://schemas/rfq-v1",
  "output_contract_ref":"artifact://schemas/quote-v1",
  "business_rules_refs":["artifact://approved/sop-v3"],
  "approved_example_refs":["artifact://examples/01"],
  "artifact_manifest_ref":"artifact://manifests/01",
  "required_capabilities":["read_xlsx","catalog_lookup","write_xlsx"],
  "allowed_effects":["read","draft_file"],
  "acceptance_policy_ref":"artifact://policies/acceptance-v1",
  "limits":{"max_steps":25,"max_usd_per_run":2},
  "snapshot_digest":"sha256:...","created_by":"authorized-owner"
}
```

A `SEALED_HOLDOUT` gold document is **never retrievable by Builder, Runtime or GEPARD**, even when its ID is guessed. The Evaluation service owns its separate ACL and gold cases. A Task Snapshot is immutable once READY; changes create a new revision. Task Intake provides only allowed read methods.

## 2. Capability Manifest — owner: agent 03

```json
{
 "schema_version":"0.1","tool_id":"catalog.lookup","version":"1.0.0",
 "operation":"search_items","transport":"MCP","input_schema_ref":"artifact://schemas/catalog-input",
 "output_schema_ref":"artifact://schemas/catalog-output","side_effects":["read"],
 "required_scopes":["catalog:read"],"risk_level":"low",
 "tenant_availability":["tenant-a"],"manifest_digest":"sha256:..."
}
```

Registry returns **zero or more eligible manifests and explicit denials** (missing permission, no capability, incompatible schema). Builder must select the smallest authorized covering set, no implicit new MCP install. Never put credentials in the manifest.

## 3. Build / AgentSpec — owner: agent 04; orchestration caller: agent 01

```json
{
  "schema_version":"0.1","build_id":"build-001","tenant_id":"tenant-a",
  "task_snapshot_id":"snap-001","idempotency_key":"build-tenant-a-snap-001",
  "capability_registry_revision":"reg-v1",
  "evaluation_policy_ref":"artifact://policies/acceptance-v1"
}
```

Suggested asynchronous API: `POST /internal/builds` → `202 {build_id,status:"QUEUED"}`; `GET /internal/builds/{build_id}`. Terminal event: `agent.assembled` or `build.failed`, includes `build_id`, `tenant_id`, `agent_spec_ref`, `agent_spec_digest`.

An immutable AgentSpec contains `tenant_id,agent_id,agent_spec_version,task_snapshot_id,selected_tools[tool_id,version,digest,granted_scopes],model_route,system_prompt_ref,harness_graph_ref,memory_policy,checkpoint_policy,a2a_card_ref,limits,artifact_digest`. Do not copy raw customer files or credentials into prompt/spec.

## 4. Runtime execution — owner: agent 04; callers: Evaluation/A2A client

Suggested API: `POST /internal/agent-runs` with `tenant_id,agent_spec_ref,request_ref,run_id,idempotency_key,budget` → `202 run_id/status`; authenticated `GET /internal/agent-runs/{run_id}` returns `status,artifact_refs,trace_ref,cost_usage,tool_effect_refs`. A2A adapter must be protocol-conformant and separate from domain harness. Only approved AgentSpec version is eligible for externally visible release.

## 5. Evaluation and optimization — owner: agent 05, commanded by agent 01

Suggested API: `POST /internal/evaluations` with `tenant_id,agent_spec_ref,dataset_version_ref,baseline_spec_ref,policy_ref,idempotency_key` → `202 evaluation_run_id`. Terminal event `evaluation.completed`: `evaluation_run_id,agent_spec_digest,dataset_version_ref,passed,hard_veto,metrics_ref,findings_ref,trace_ref`. The independent evaluator, not candidate agent, owns the PASS decision and sealed holdout.

Suggested `POST /internal/optimizations` with `tenant_id,agent_spec_ref,baseline_spec_ref,allowed_surfaces,train_validation_refs,budget,idempotency_key` → `202 optimization_run_id`. GEPARD reads tenant-authorized AgentSpec/trace excerpts, only proposes a **new immutable candidate**. It cannot mutate a released agent or see holdout answers. Re-evaluate candidate independently. Model savings benchmarking is Evaluation-owned and uses LiteLLM, with quality non-inferiority or INCONCLUSIVE result.

## 6. Release and AgentStore — owner: agent 01

Proposed `POST /internal/releases` command: `tenant_id,agent_spec_ref,evaluation_run_id,required_approvals,policy_ref,idempotency_key`. The release manager checks immutable evidence, hard vetoes, approvals and rollback. Versioned AgentStore metadata: `agent_id,tenant_id,version,channel,agent_spec_digest,tool_digests,model_route_digest,release_evidence_refs,a2a_card_ref,rollback_ref`. Proposed channels `candidate/verified/released/rolled_back`. No direct external A2A exposure before RELEASED.

## 7. Error/status vocabulary

Task: `DRAFT/INGESTING/REQUIRES_CLARIFICATION/READY/BLOCKED`. Build: `QUEUED/RUNNING/ASSEMBLED/FAILED/BLOCKED`. Evaluation: `QUEUED/RUNNING/PASSED/FAILED/BLOCKED/INCONCLUSIVE`. Release: `CANDIDATE/VERIFIED/RELEASED/ROLLED_BACK`.

Failures include machine-readable `code`, `detail`, `retryable`, `trace_id`, `required_action` with secrets and confidential partner data redacted. A model response saying "done" without tool-effect evidence is never success.

## Contract change protocol

Agents SHALL NOT edit this file. A change proposal belongs in the owning module PR: request/response example, versioning and migration plan, compatibility impact, owner review required. Consumer mocks may reflect this v0; unresolved gaps are clearly marked PROPOSED.
