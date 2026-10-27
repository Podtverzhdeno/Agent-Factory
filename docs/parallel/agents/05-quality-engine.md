# AGENT 05 — Independent Evaluation, GEPARD and Model Benchmark

**Branch:** agent/05-quality-engine
**You own only:** \`services/evaluation/**\`, \`services/gepard-optimizer/**\`, \`tests/quality-engine/**\`
**Stack:** Python 3.12+, Pydantic, evaluation workers + isolated GEPARD adapter, DSPy/GEPA where real package available, fake LiteLLM/Agent Runtime ports for tests. Evaluation and optimizer must keep independent data/permissions even under one developer owner.
**Relevant requirements:** AF-REQ-008/009/010/011/017 (research optional), AF-REQ-019/020, AF-REQ-028, AF-REQ-041/042/043/044/048.

## One independently owned task

Independently evaluate a candidate specialized agent on structured business tasks, observe tool/ReAct/memory/A2A behavior, produce measured error taxonomy and orchestrator-readable scores. Allow GEPARD to propose isolated new prompt/tool-description candidates from approved tuning data. Add a model cost/quality benchmark that can return PASS/FAIL/INCONCLUSIVE. Nothing can bypass release or read sealed gold.

## Separation of trust inside this work packet

- **Evaluation** alone owns hidden holdout/oracle files and makes safety hard-veto decisions. It never sends gold correct answers to GEPARD.
- **GEPARD** can read only approved training/validation cases and sanitized errors. Propose immutable prompt/model-facing description candidate with hash, not direct edits to serving runtime.
- **Model Benchmark** is Evaluation-owned, compares pinned baseline with eligible candidate via LiteLLM-like port; model choice is qualified by business non-inferiority, end-to-end cost per correctly completed task, p95 latency, tool compatibility, privacy constraints and owner thresholds.

## Deliverables

1. Typed \`EvaluationRequest\`, \`EvaluationResult\`, \`Finding\`, \`BenchmarkResult\` with dataset/policy version, agent spec hash, trace refs and honest BLOCKED/INCONCLUSIVE.
2. Fixture scorer for synthetic chemical RFQ and certificate validation (correct artifacts, source checks, required real tool-effect proof); semantic self-claims are not sufficient.
3. Structured metrics for task correctness, tool-selection, argument schema, ReAct observable transitions, memory stale/cross-tenant conditions, latency/tokens/cost and safety hard gate.
4. Strict separation of tuning vs validation vs sealed holdout data using denied-access tests and duplicate/leak checks.
5. GEPARD adapter that proposes a new immutable AgentSpec-config patch on synthetic known bad prompt; mock optimizer if external integration cannot be executed, explicitly label it.
6. Cost-quality model comparison: cheaper candidate rejected on missing tool calling, privacy region, unacceptable regression; insufficient held-out cases returns INCONCLUSIVE. Full request cost includes retries/fallbacks.
7. Independently runnable mock Runtime tests and README with executed proof and limitations.

## Acceptance

Tests prove an agent that writes fluent "completed" text but misses a required tool call FAILS; a successful deterministic candidate passes if its real output artifact is correct; unseen holdout is never accessible to optimizer; benchmark does NOT auto-promote an unproven cheaper model. Works without live Builder/Runtime/Orchestrator.

## Exclusions

Do not control the Orchestrator/AgentStore release gate (01), invent tool grants (03), mutate real deployed Runtime (04), access another tenant's confidential documents (02), train Soup in P0 or make bilateral A2A acceptance mandatory.

## Copy/paste launch prompt

> Implement Agent Factory workstream **05 Quality Engine** on branch **agent/05-quality-engine**. Read \`AGENTS.md\`, \`docs/parallel/README.md\`, \`docs/parallel/CONTRACTS_V0.md\`, \`docs/architecture/TWIN_AGENT_HARNESS_RFC.md\` and this file. Own only \`services/evaluation/**\`, \`services/gepard-optimizer/**\`, \`tests/quality-engine/**\`. Implement mock-backed independent evaluator, separate GEPARD candidate adapter and cost-quality benchmark with strict holdout privacy and negative tests. Open PR targeting \`docs/sdd-foundation-mvp\` with reproducible test output, clear BLOCKED features and no shared/foreign file edits.
