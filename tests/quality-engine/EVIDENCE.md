# Agent 05 evidence (local component tests)

- Workstream: independent Evaluation / GEPARD candidate adapter / Model Cost–Quality Benchmark
- Branch: `agent/05-quality-engine`
- Test inputs: synthetic chemical RFQ and certificate verification; deterministic mock tools, memory violations and model usage
- Python: 3.13.5
- Command: `pytest -q tests/quality-engine`
- Observed: **30 passed in 0.06s**
- Command: `pytest --cov=quality_engine --cov=gepard_optimizer --cov-report=term-missing -q tests/quality-engine`
- Observed: **30 passed in 0.14s; 95% statement coverage** over the locally staged code
- Command: `python -m compileall -q services`
- Observed: **passed**
- Only source-owned files under `services/evaluation/`, `services/gepard-optimizer/`, `tests/quality-engine/` were submitted

## Assertions verified by component tests

- Both independent synthetic business cases validate expected artifacts and recorded tools
- Fluent false success with absent mandatory tool effect FAILS
- Unauthorized tools, memory violations force safety veto
- Missing trace, schema invalid tool, graph step limit diagnosed
- Evaluation role can access private holdout; optimizer, builder and runtime cannot
- Dataset gold records are immutable across caller mutations and versioned references
- Reusing idempotency key with changed evidence fails
- PASS on tuning-only cases is **not** independent acceptance evidence
- Model candidate with lower cost and noninferior held-out results can PASS on synthetic runs; observed degradation, safety or capability regression FAIL; small samples are INCONCLUSIVE
- GEPARD mock produces immutable candidate only, never mutates agent or bypasses release
- DSPy GEPA import/budget/strict train-validation wiring is unit tested via fake DSPy module, **not live GEPA optimization**

## Remaining limitations / explicit BLOCKED integration

These tests are local and synthetic, **not GitHub Actions domain tests**, production IAM or business pilot validation. The GitHub SDD workflow currently validates specifications, not this Python suite; integrator must add a first-class code CI job after owner approval of shared CI changes.

No real Runtime, LiteLLM, Langfuse, eventing, Java orchestrator, external MCP, API security service, persistent dataset vault or actual authorized gold provenance is integrated. `DatasetVault` is an in-process role-scoped fake, **not a secure production store**; near-duplicate input detection is not complete. Tool-effect proofs are trusted mock evidence and must be checked against authenticated runtime audit events before rollout. Agent 01 owns release policy and approvals. ADR-0002 remains pending owner ratification.

All functionality must be independently code-reviewed, security-tested and end-to-end integrated before claiming the platform works.
