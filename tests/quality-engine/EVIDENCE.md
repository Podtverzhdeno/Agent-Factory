# Agent 05 — verified component evidence

## Executed locally, Python 3.13.5
- `pytest -q tests/quality-engine`: **49 passed**
- `pytest --cov=quality_engine --cov=gepard_optimizer --cov-report=term -q tests/quality-engine`: **49 passed, 96% statement coverage** (567 statements, 25 missed)
- `python -m compileall -q services`: **passed**
- CI on PR validates OpenSpec/SDD; it does NOT execute this component suite.

## Completed component milestones
1. Independent domain scoring for chemical RFQ and certificate cases against private versioned gold.
2. Denial of missing tool calls, missing effect proofs, invalid tool arguments, unauthorized actions, policy/tenant violations, incorrect outputs, ReAct missing transitions, stale or cross-tenant memory and graph step overflow.
3. Holdout vault: train/validation/holdout role separation, immutable gold copies, duplicate input reference screening across tune/holdout and no hidden labels passed into execution collector (PublicRunCase).
4. Typed EvaluationWorkflow state and HTTP contract: explicit submit returns 202 QUEUED; internal worker processes with authenticated principal port; idempotency, safe tenant-scoped lookup, fail closed on untrusted collector errors. Collector envelopes pinned to exact tenant, AgentSpec digest, dataset, case and provenance reference.
5. GEPARD immutable candidate adapter + optional DSPy GEPA invocation seam; execution still MOCK, no live optimization.
6. Model cost-quality: pinned paired cases, required capabilities/region, retry/tool/fallback spend, exact statistical upper bound without large-N underflow, reject NaN and quality regression; requires explicit independently verified holdout provenance or reports INCONCLUSIVE.
7. Synthetic component integration: baseline fails missing catalog proof → permitted immutable mock prompt patch → independent holdout retest passes; no production release.

## Boundaries still NOT completed

**This is not a production-ready independently deployable service.** ADR-0002 still awaits owner ratification. Authentication is injected from a trusted integration port; its production implementation is NOT included. Data stores, job state and DatasetVault remain **in memory** (not PostgreSQL or cloud object storage). Collector envelope is typed and validated but is NOT a cryptographic attestation: authenticated Runtime/A2A tool audits must be integrated. The exact/gold fingerprint check is not robust near-duplicate detection.

GEPARD is NOT actually optimizing a DSPy program using a paid/private model; test uses a deterministic mock or fake DSPy object to verify adapter contract. LiteLLM, LangGraph, Kafka, Langfuse, actual customer files and cost provenance have not been integrated. The model benchmark synthetic success Boolean is not authoritative without real authenticated Evaluation inputs. Quality gates and released versions belong to Agent 01 Orchestrator.

## Requirement mapping and remaining tasks

- AF-REQ-008/009/028: core evaluator and dataset isolation component implemented/tested; real gold storage, end-to-end trace provenance and security integration pending.
- AF-REQ-010/011/041: mock GEPARD proposal implemented/tested; real DSPy feedback loop, quotas and runtime candidate integration pending.
- AF-REQ-019/020/042/043: trace, observable ReAct and memory negative checks implemented/tested on synthetic evidence; real traces and persistence pending.
- AF-REQ-048: standalone statistical model comparison implemented/tested; real LiteLLM metering, pricing snapshots, holdout authorization and release gate integration pending.

Do NOT mark end-to-end SDD implementation tasks complete, and do NOT merge without independent code review and owner-approved ADR.
