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
