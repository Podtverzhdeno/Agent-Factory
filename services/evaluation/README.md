# Evaluation and Model Cost–Quality Benchmark — workstream 05

**Scope:** isolated mock-backed Python quality domain with deterministic artifact, trace and business-effect checks; tenant-scoped gold vault and holdout separation; paired model cost-quality benchmark.

Source: `quality_engine/core.py`. Test with `pytest -q tests/quality-engine` at repo root (pytest installed). Contracts: `docs/parallel/CONTRACTS_V0.md` read-only.

**Critical caveat:** this is a component proof, NOT a deployed independent Evaluation API. There is no production identity provider, PostgreSQL, artifact ingestion, Langfuse, Kafka, real customer datasets or connected Agent Runtime. Evaluations accept trusted test `ObservedRun` objects; evidence provenance must eventually be authenticated against Agent Runtime/audit logs, not caller assertions. In-memory dataset vault enforces role restrictions within this process; it is NOT an external security boundary. Its fingerprint comparison is exact, not near-duplicate detection. No service is authorized to release agents based solely on these tests.

Supported evidence: precise structured output artifacts; required authorized tool call and evidence proof; tool argument validity; observable graph step/trace; memory/safety hard gates; latency and total cost. Aggregated event payload contains no gold content. Holdout access blocked for optimizer/builder/runtime.

Benchmark: paired immutable cases, required model capability/processing region, conservative one-sided bound on candidate loss frequency, successful-operation cost including model, retry, tool and fallback. Requires enough independent cases and policy-defined noninferiority threshold. A synthetic pass is not production proof.

Requirements: AF-REQ-008/009/019/020/028/042/043/048. Remaining: authenticated endpoints, persistent vault, streamed callbacks, real agent execution, verified tool side effects, model-provider billing/reconciliation, evaluator/optimizer separate deployment and full E2E.


## New contract-first application adapter

- `quality_engine.primitives`: identities and hashing
- `quality_engine.datasets`: immutable test fixtures and isolated holdout vault
- `quality_engine.evaluation`: pure business and ReAct/memory scoring
- `quality_engine.model_benchmark`: paired non-inferiority and cost comparison
- `quality_engine.application`: stateful idempotent evaluation workflow and trusted `EvidenceCollector` protocol
- `quality_engine.api`: proposed FastAPI adapter. **A trusted identity dependency is mandatory**; do not expose it using a caller-controlled tenant header. `POST /internal/evaluations` returns 202 QUEUED, a worker separately processes evidence, and `GET /internal/evaluations/{run_id}` shows state to an authorized tenant.
- `quality_engine.core`: compatibility facade to preserve existing imports while allowing modular domain design.

The execution collector receives only `PublicRunCase(case_id,input_ref)`, never evaluator gold labels. It returns `EvidenceEnvelope` tied to a pinned candidate/dataset/tenant with audit trace reference; actual cryptographic trace provenance must be integrated later.

Model Benchmark requires `BenchmarkEvidence` proving an independently owned holdout and separate baseline/candidate trace refs before returning PASS. References are not cryptographically attested in the component prototype, therefore release decisions remain external.

Install optional HTTP extra `api` from the evaluation package and `test` for tests. No standalone process or production secret manager is configured in this PR.


## Durable evaluation and encryption-first storage

The SQLAlchemy store includes immutable per-tenant gold datasets, evaluation job leases with fencing tokens, expired-worker BLOCKED reaping, and a transactional completion outbox. `DurableEvaluationWorkflow` requires verified runtime signatures before scoring. `OutboxPublisher` waits for a transport ACK before marking events sent. Delivery is at least once; consumers must de-duplicate by `event_id`. **Kafka and PostgreSQL were not contacted in the current environment.**

`SqlDatasetVault` now defaults to **require_encryption=True**. A tenant-scoped AES-256-GCM key must be injected by trusted KMS infrastructure; associated data binds tenant, dataset version and case. Only isolated test fixtures may explicitly set `require_encryption=False`. No production secrets should be placed in source, AgentSpec or business files.

For the real PostgreSQL opt-in test, see `POSTGRES_INTEGRATION.md`. For Runtime signed audit handoff see `CONTRACT_CHANGE_REQUEST.md` and Agent 04 PR #3.


## 2026-10-27 cross-service security updates

- `quality_engine.runtime_http.RuntimeEvidenceHTTPCollector`: read-only, bounded signed-audit HTTP retrieval from a pre-executed sandbox Runtime run. Requires HTTPS except local loopback, a trusted service bearer token, strict observed-run schema and **signature verification by the workflow**. Public `input_ref` is not placed in GET query strings; hidden gold is never sent.
- `quality_engine.execution_evidence.EvidenceEnvelope` includes signed `evaluation_run_id` to prevent stale audit replay. Different evaluations of the same task cannot reuse one another's signed evidence.
- `quality_engine.lease_heartbeat.LeaseKeeper`: fenced automatic renewal while evaluation is running, allowing slow tests to finish without duplicate worker claims; external actions still need independent idempotency.
- Ed25519 verifier can consult an injected revocable/expiring trusted public-key provider. A live key management service and Agent 04 signed producer are NOT yet connected.
- Current local verification: **117 passing, 3 deliberately skipped external tests**, statement coverage 93%. See `tests/quality-engine/EVIDENCE.md`.
