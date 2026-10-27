# Quality Engine — architecture review & closure criteria

**Scope:** Agent 05 only. Current state: **component implementation verified locally, integration NOT accepted**. Owner ADR-0002 still requires independent GitHub ratification. This file is a review record, not an ADR.

## Clean boundaries

| Module | Responsibility | Forbidden dependency |
| --- | --- | --- |
| `quality_engine.primitives` | immutable tenant identity, canonical evidence digest utility | FastAPI/DB |
| `quality_engine.datasets` | sealed gold, split ACL, immutable fixture refs | Agent Runtime model internals |
| `quality_engine.evaluation` | independent deterministic business/tool/graph/memory verdict | optimizer, LiteLLM, HTTP |
| `quality_engine.model_benchmark` | conservative paired model quality, latency and total cost | provider transport |
| `quality_engine.application` | evaluation job state/ports, evidence validation, idempotency | Kafka specific driver |
| `quality_engine.api` | proposed FastAPI serialization with mandatory auth dependency | embedded authentication secrets |
| `gepard_optimizer.core` | immutable candidate proposal only | Evaluation hidden gold / production release |
| `gepard_optimizer.dspy_backend` | optional GEPA optimizer integration port, bounded metric calls | direct agent promotion |

Interfaces shared with other agents: `POST /internal/evaluations` → 202 QUEUED, `GET /internal/evaluations/{run_id}`; Evaluation emits only sanitized metrics/evidence refs; GEPARD returns a candidate and cannot declare VERIFICATION or RELEASED. All actual external evidence should arrive only through `EvidenceCollector`, not HTTP payloads. Runtime receives only public input, never hidden answer fields.

## Requirements and honest status

| Reference | Current component proof | What prevents closing the complete requirement |
| --- | --- | --- |
| AF-REQ-008/009 | business artifact + required tool-effect checks, hard veto and independent holdout flag tested | authenticate external effects and service-owned gold in persistent storage |
| AF-REQ-010/011 | deterministic optimizer candidate and synthetic candidate/holdout regression demo | live DSPy GEPA backed by authorized gateway, scored experiments and resource budgets |
| AF-REQ-019/020 | structured trace identifiers, tenant and tool/memory guards, adversarial synthetic tests | real OTel/Langfuse, tenant IAM, physical isolation, real trace redaction |
| AF-REQ-028 | test vault denying builder/runtime/optimizer on sealed gold, exact matching source contamination | persisted encrypted dataset store, independent IAM/keys, near-duplicate corpus screening |
| AF-REQ-041/042 | trace-observable tool/ReAct transition errors, no hidden model reasoning | live LangGraph trace validation and tool/MCP SDK contracts |
| AF-REQ-043 | stale/unauthorized long-term memory evidence catches in synthetic traces | connected short/long-term memory store, crash/restart corpus and deletion proof |
| AF-REQ-048 | conservative paired benchmark with provenance requirement, large-N stable CDF and total-attributable cost | real LiteLLM billing/usage, dataset-independent trial stratification and owner non-inferiority policy |

**Do not mark T05, T06, T13, T14, T20, T33, T34, T35 or T40 fully closed at project level until their external integration evidence exists.** Testing only mocks is not equivalent to a working factory.

## Integration conditions to unblock (owner + integrator)

1. Ratify ADR-0002 by a real owner GitHub action. Decide durable Evaluation queue/database, required service IAM and actual service deployment topology.
2. Agent 04 publishes versioned Runtime execution/audit API with verifiable tool-effect provenance, signed AgentSpec hash and tenant identity.
3. Agent 02 provides scoped file/object access and immutable dataset packaging. Hidden holdout dataset storage must belong to Evaluation, not Builder.
4. Agent 01 provides idempotent Evaluation command orchestration and independent release policy; the Evaluation service must never issue deployment mutations itself.
5. Approved LiteLLM inference and spending backend plus allowed model/provider combinations. Require measured cost and limits for the GEPA reflection LM.
6. Implement durable job state, retries/DLQ, auditing, private encrypted gold storage, external auth, tracing and retention for deployed Evaluation/GEPARD.
7. Run domain E2E using both business fixtures, cross-tenant negative tests, injected crashes, real tool-effect records, held-out model comparison and rollback.
8. Integrator updates shared CI (not workstream 05): install module test extras and execute `pytest -q tests/quality-engine`, lint/type and coverage thresholds on every PR.

## Evidence available

Local Python 3.13.5: `pytest -q tests/quality-engine` -> **50 passed**; `pytest --cov=quality_engine --cov=gepard_optimizer --cov-report=term -q tests/quality-engine` -> **96% coverage**, `python -m compileall -q services` -> **passed**.

GitHub Actions on the workstream PR currently checks SDD/OpenSpec only, not the above Python suite. Real GEPA optimization has **not** been executed; module import/contract is validated against fake dspy and optional dependency. 50 tests are strong component evidence but not business acceptance.
