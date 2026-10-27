# Evaluation and Model Cost–Quality Benchmark — workstream 05

**Scope:** isolated mock-backed Python quality domain with deterministic artifact, trace and business-effect checks; tenant-scoped gold vault and holdout separation; paired model cost-quality benchmark.

Source: `quality_engine/core.py`. Test with `pytest -q tests/quality-engine` at repo root (pytest installed). Contracts: `docs/parallel/CONTRACTS_V0.md` read-only.

**Critical caveat:** this is a component proof, NOT a deployed independent Evaluation API. There is no production identity provider, PostgreSQL, artifact ingestion, Langfuse, Kafka, real customer datasets or connected Agent Runtime. Evaluations accept trusted test `ObservedRun` objects; evidence provenance must eventually be authenticated against Agent Runtime/audit logs, not caller assertions. In-memory dataset vault enforces role restrictions within this process; it is NOT an external security boundary. Its fingerprint comparison is exact, not near-duplicate detection. No service is authorized to release agents based solely on these tests.

Supported evidence: precise structured output artifacts; required authorized tool call and evidence proof; tool argument validity; observable graph step/trace; memory/safety hard gates; latency and total cost. Aggregated event payload contains no gold content. Holdout access blocked for optimizer/builder/runtime.

Benchmark: paired immutable cases, required model capability/processing region, conservative one-sided bound on candidate loss frequency, successful-operation cost including model, retry, tool and fallback. Requires enough independent cases and policy-defined noninferiority threshold. A synthetic pass is not production proof.

Requirements: AF-REQ-008/009/019/020/028/042/043/048. Remaining: authenticated endpoints, persistent vault, streamed callbacks, real agent execution, verified tool side effects, model-provider billing/reconciliation, evaluator/optimizer separate deployment and full E2E.
