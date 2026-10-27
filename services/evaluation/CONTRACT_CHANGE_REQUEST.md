# Contract Change Request — Agent Runtime ↔ Quality Evaluation

Status: PROPOSED. Agent 04 and owner review required; ADR-0002 remains pending. Only workstream 05 paths changed.

## Problem

Agent 04 currently returns RunResult(status, run_id, trace_id, answer, tool_effect_refs, cost_usd, steps). This alone cannot independently verify business artifacts and trusted tool execution. Claiming completion in natural language must NEVER be accepted as proof.

## Proposed read-only authenticated audit contract

- Evaluation starts a sandbox run using only PublicRunCase(case_id, input_ref), tenant-scoped authorized AgentSpec; it NEVER passes hidden expected answers.
- An authenticated GET /internal/agent-runs/{run_id}/evaluation-evidence returns schema_version, tenant_id, agent_spec_digest, dataset_version_ref, case_id, trace_ref, audit_id, issued_at and signer key_id.
- ObservedRun includes verifiable structured business artifact or artifact hash/reference, every trusted tool call/argument validation/permission, effect proof IDs, observable graph events, latency/spend and approved scoped memory evidence.
- The Runtime service signs canonical JSON bound to all fields. An LLM can neither write the audit ledger nor select signer secrets. Production mTLS/service IAM, signer key rotation and revocation remain infrastructure responsibilities.
- Quality verifies the signature and exact pinned tenant/spec/dataset/case, reconciles independently sourced effect proofs, then scores privately against sealed gold. Raw prompt/tool secrets and gold never enter Kafka.
- The signed claim must come from the trusted Runtime audit/tool gateway, not from an LLM-generated answer or a client-controlled header.

## Mandatory cross-service negative tests

1. Fluent 'done' but missing required tool effect -> FAIL.
2. Tampered case/tenant/spec/artifact/tool effect -> BLOCKED.
3. Duplicate external effect during resume -> BLOCKED until external reconciliation.
4. Revoked or foreign signer/tenant -> access denied.
5. Runtime is unaware of expected holdout answer, sees public input only.
6. AgentStore release remains owned by Agent 01, never by Quality or Runtime.

## Ownership

Agent 04 owns producer/Runtime audit; Agent 05 owns consumer/independent scoring; Agent 01 owns release.
This request is not a change to frozen shared CONTRACTS_V0 and not architecture ratification. See PR #2 and PR #3.


## Mandatory 2026-10-27 signed-audit schema extension

**Each signed Runtime audit envelope MUST contain `evaluation_run_id`** as part of the canonical Ed25519-signed JSON in addition to tenant, AgentSpec digest, dataset version, case, trace and actual observed tool effects. Quality rejects replay of signed evidence from a previous evaluation run even when all other identifiers match.

Consumer endpoint proposed: authenticated `GET /internal/agent-runs/{evaluation_run_id}:{case_id}/evaluation-evidence?case_id=...&tenant_id=...&agent_spec_digest=...&dataset_version_ref=...`. The colon is URL-encoded and input files are **not sent as GET query parameters**. Creation of sandbox runs is a separate Orchestrator/Runtime responsibility; Quality only reads authoritative completed audits.

Producer must emit JSON `{envelope: {tenant_id,agent_spec_digest,dataset_version_ref,case_id,trace_ref,observation,evaluation_run_id},key_id,signature_hex}` with the Ed25519 signature over canonical JSON (`sort_keys=True`, compact separators, no NaN) of `envelope`. Exact `ObservedRun` typed fields follow `quality_engine.evaluation.ObservedRun`. Runtime private signing keys never enter Evaluation; the verifier reads trusted tenant-scoped public keys with revocation/validity checks via secure resolver.

Current consumer code: `quality_engine/runtime_http.py`, `execution_evidence.py`, `ed25519_audit.py`. It passes real loopback TCP integration to an **in-process signed test server**, not yet to Agent 04's actual Runtime. Producer implementation and transport IAM remain OPEN on PR #3.
