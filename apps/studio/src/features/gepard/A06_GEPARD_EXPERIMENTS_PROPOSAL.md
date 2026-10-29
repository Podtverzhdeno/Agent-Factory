# A06 — GEPARD experiment and independent retest proposal

**Status: PRE-C0 RESEARCH ONLY. No executable UI or live optimizer claim.**  
**Task:** STU-T08 / A06 · [Issue #13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13)  
**Branch:** research/a06-pre-c0-quality-20261028. Not C0; no lease granted.

## 1. Current source evidence

- [GEPARD README](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/services/gepard-optimizer/README.md): default backend is deterministic mock, not DSPy GEPA; it returns a candidate proposal with a digest and REQUIRES_INDEPENDENT_EVALUATION.
- [Optimizer implementation](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/services/gepard-optimizer/gepard_optimizer/core.py): pins tenant and source AgentSpec, permits only system_prompt or tool_description, bounds candidates to 1–10, requires distinct tuning/validation refs, and rejects holdout/sealed inputs. It must not change application code, MCP grants or safety policy.
- [Optional DSPy bridge](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/services/gepard-optimizer/gepard_optimizer/dspy_backend.py): call wiring for dspy.GEPA is optional and tested with a fake DSPy module. That verifies the adapter shape, not a real optimization run or quality improvement.
- [Latest Evaluation evidence snapshot](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/tests/quality-engine/EVIDENCE.md): live DSPy/GEPA is skipped unless explicit paid-inference authorization, an approved gateway/model and credentials are provided.
- [Control Plane README](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/01-control-plane/services/factory-orchestrator/README.md): optimizer outcomes are proposals; default wiring does not enable live remote clients or release.
- [AF-REQ-108](https://github.com/Podtverzhdeno/Agent-Factory/blob/design/frontend-studio-rfc-20261028/openspec/changes/studio-cjm-parallel/specs/studio-cjm/spec.md): a mock or regressing candidate cannot be shown as measured live improvement or promoted.

## 2. Proposed experiment lifecycle

1. **READY_TO_PROPOSE** — authenticated actor has server-returned allowed action; current baseline digest and server cap are known.
2. **QUEUED / RUNNING** — accepted operation has durable experiment ID/receipt. Retry after a lost response must query the same operation, not silently create another paid run.
3. **CANDIDATE_PROPOSED** — immutable candidate and source-baseline digests, backend type/version, allowed change surface, scrubbed diff, attempt count and evidence provenance.
4. **RETEST_REQUIRED** — independent Evaluation must test the exact candidate digest on a separately authorized dataset revision and evaluation policy.
5. **RETESTING** — candidate only runs in authorized sandbox; production prompt/harness and tool grants remain unchanged.
6. **ACCEPTED_FOR_RELEASE_REVIEW** — independent Evaluation satisfies hard gates and predeclared non-inferiority/regression rules. This is not a release state.
7. **REJECTED / BLOCKED / INCONCLUSIVE / UNAVAILABLE** — explicit non-success state with safe source-owned reason and allowed recovery action.

These names are proposed UI states, not claims about deployed upstream enums. I00/A01 must map real API states through a versioned contract. Unknown values fail closed.

## 3. Experiment evidence model

Each experiment should carry:
- tenant-scoped immutable baseline AgentSpec ref/digest;
- candidate ref/digest and patch digest; changed surface and sanitized diff;
- optimizer backend and version, with truthful MOCK / DSPY_GEPA_REAL / other verified identity;
- experiment ID, stable idempotency reference, source-owned state and source timestamp;
- maximum candidates, metric-call cap, attempt count, deadline and spend cap, with requested limit separate from measured actual spend;
- tuning and validation dataset refs and revisions, distinct from sealed acceptance holdout;
- independent retest run ID, exact candidate digest, evaluator policy, dataset revision, verdict and source evidence reference;
- source completeness/freshness, audit reference and safe error;
- outcome denominator, findings, hard veto, latency and attributed cost when genuinely measured;
- environment, action permissions and role-safe evidence links.

Never render sealed holdout IDs, expected answers, private prompts or another tenant's data. Server-side redaction is required; client hiding alone is not sufficient.

## 4. Bounded budget and recovery

- Server policy is authoritative for candidate count, metric calls, attempts, deadline, approved model/provider and cost ceiling.
- Show requested caps separately from actual spend. Missing or unreconciled billing means unknown/unavailable, not zero and not “budget spent”.
- A larger cap is a new authorized, audited request. A failed or timed-out run must not auto-widen the budget.
- Timeout, lost reply or source outage requires querying the original operation by stable ID/idempotency. Do not blindly re-run paid inference.
- Baseline digest drift, permission change, dataset change or unsupported optimizer version invalidates eligibility and requires reconciliation.

## 5. Independent retest rules

- Evaluation remains independent from optimizer; sealed holdout data never enter GEPARD input or browser details.
- Pin candidate digest, baseline digest, dataset revision, evaluator policy version and runtime/tool schema.
- Compare equivalent cohorts and report denominator/exclusions/uncertainty where supported.
- Any safety veto or mandatory tool/effect regression rejects the candidate, regardless of mean quality or price.
- Missing signature, required external receipt, gold, provenance or enough samples means BLOCKED / INCONCLUSIVE / UNAVAILABLE, not probable PASS.
- A successful retest only qualifies for separate release-policy review. Any subsequent candidate edit invalidates the old retest.

## 6. Truthful rendering matrix

| Evidence | Safe label | Do not claim |
|---|---|---|
| Default deterministic adapter | Mock optimizer — synthetic candidate | GEPA executed / live improvement |
| Fake injected DSPy object | DSPy adapter contract-tested | Real GEPA executed |
| Real optimizer, no independent retest | Candidate proposed — retest required | Verified / safe to release |
| Independent retest with insufficient samples | Inconclusive | Equivalent / non-regression proven |
| Evaluation passed, release not confirmed | Evaluation passed; release gates pending | Released / deployed |
| Source unavailable or stale | Unavailable / stale with source timestamp | Zero candidates, zero cost or success inferred from missing data |

## 7. Request to I00/A01

1. Freeze typed APIs to list experiments, submit bounded idempotent requests, poll receipts and fetch candidate diffs.
2. Include backend/version, baseline/candidate digests, permitted surface, budget and actual-usage distinction, dataset refs, state, source stamps and safe errors.
3. Define 401/403/409/429/503 semantics; a 409 must not reveal another tenant's data.
4. Define role-based prompt diff/artifact access; redact secrets server-side.
5. Provide independent Evaluation retest command and read APIs with exact candidate digest and audit ref.
6. Keep AgentStore promotion and live deployment under source-authoritative Control Plane/AgentStore; never call internal optimizer services from the browser.

No live optimization was run by this research task. No paid inference, customer data, production credentials or release action was used.