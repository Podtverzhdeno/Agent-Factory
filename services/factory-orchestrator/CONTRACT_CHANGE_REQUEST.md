# Workstream 01 — proposed v0.1 integration compatibility questions (owner review required)

**Status:** DRAFT / NOT APPROVED. This file is local to workstream 01. It does not change `docs/parallel/CONTRACTS_V0.md` or ratify ADR-0002.

## Direct commands implemented behind typed ports

| Upstream | Path | Sent fields | 202 response required |
| --- | --- | --- | --- |
| Agent Builder (04) | POST /internal/builds | schema_version, tenant_id, task_snapshot_id, snapshot_digest, idempotency_key, correlation_id, operation_id, evaluation_policy_ref | build_id, status=QUEUED/RUNNING/ACCEPTED |
| Independent Evaluation (05) | POST /internal/evaluations | schema_version, tenant_id, agent_spec_ref, agent_spec_digest, baseline_spec_digest, dataset_version_ref, policy_ref, idempotency_key, correlation_id, operation_id | evaluation_run_id, status |
| GEPARD (05) | POST /internal/optimizations | schema_version, tenant_id, agent_spec_ref, agent_spec_digest, baseline_spec_ref, baseline_spec_digest, train_validation_refs, allowed_surfaces, idempotency_key, correlation_id, operation_id | optimization_run_id, status |

Local HTTP adapters refuse non-202 or ambiguous receipts. A remote retry is safe only if the target deduplicates by (tenant_id,idempotency_key). Remote API implementation, JWT issuer, test dataset and sealed holdout are owned by other workstreams.

## Compatibility questions — must be resolved before real end-to-end acceptance

1. Upstream v0 examples do not consistently require `operation_id` in request and completion events. Require an echoed operation ID, tenant, correlation ID, schema version and cryptographically pinned spec digest so a received event can only acknowledge its original command.
2. The draft optimizer request represents `allowed_surfaces` and `train_validation_refs` as simplified strings. Confirm the canonical arrays/object contracts and breaking-change versioning. No holdout answers may enter Builder/GEPARD.
3. Confirm independent Evaluation attestation format and secure lookup for `EvidenceVerifier`. The default Spring wiring deliberately rejects every release until an independently authenticated evaluator is connected.
4. Confirm runtime service token flow (issuer, audiences, scopes, rotation, tenant binding). There are no real secrets, anonymous fallback or implicit discovery in workstream 01.
5. Confirm HTTP timeout/retry taxonomy for 401/403, 409, 429, 5xx and transport disconnect. A timeout after 202 acceptance must reconcile by idempotency key before any business side effect is retried.
6. Confirm new immutable candidate revision carries every changed digest (especially tool selection and model-route digest after optimization). The optimizer currently returns only spec ref/digest in the proposed v0 event, so real promotion requires an independently fetched and revalidated AgentSpec manifest.
7. Confirm customer approval actor and immutable approval ID, rather than inferring approval from a plain `release:approve` scope. Human approvals must be bound to exact candidate/version, risk, tenant and expiry.
8. Confirm responsibility for operating post-release traffic switching, A2A exposure, canary checks and rollback commands. This workstream only changes AgentStore metadata.

## Schema and storage proof

- PostgreSQL V1 and forward-only V2 migrations live under `services/factory-orchestrator/src/main/resources/db/migration/`.
- `JdbcWorkflowLedger` and `JdbcAgentStore` optionally share `JdbcTransactionScope` to atomically commit candidate registration and state changes. No default deployment or DB ownership is asserted.
- V2 uses `(tenant_id,event_id)` uniqueness for the durable inbox. Duplicates within a workflow are checked by deterministic typed SHA-256 payload fingerprint; reused IDs for another workflow are denied.
- Broker notifications are at-least-once with stable IDs; durable dispatch leases, retries with jitter, dead-letter/reconciliation, retention and horizontal scaling are still open.

## Acceptance evidence requested from owners

- Team 04: independently running Builder endpoint, authenticated request/202 receipt, built artifact digest, terminal event
- Team 05: independently running Evaluation/GEPARD, sealed holdout ACL, signed evaluation result, rejected spoofed attestation
- Team 01: green exact-commit Java+Maven+Docker/PostgreSQL suite, restart/retry and real HTTP E2E, security review
- Owner: explicit ADR-0002 GitHub ratification before promoting any PoC schema/wiring to production
