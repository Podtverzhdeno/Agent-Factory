# A06 — Evaluation Scorecard: source-backed proposal

**Status: PRE-C0 RESEARCH ONLY. No executable UI and no implementation claim.**  
**Task:** A06 / STU-T08 · [GitHub Issue #13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13)  
**Branch:** research/a06-pre-c0-quality-20261028. Base is the Studio specification branch, not C0.  
**Claim/lease:** none. Issue is BACKLOG / WAITING_FOR_C0, owner=null, generation=0; coordinator NOT_DEPLOYED.

## 1. Decision summary

Evaluation is an independent source-owned verdict. GEPARD output is only a candidate proposal. Release and rollback are separate Control Plane / AgentStore decisions. Browser presentation may display provenance and initiate authorized commands, but must never mint any of these states.

**PASSED Evaluation is not RELEASED.** Release requires the exact pinned version, current authorization, every required approval, valid independent evidence, an available authorized target and a confirmed source-owned command result. A mock optimizer's proposal is not measured improvement.

## 2. Authority and evidence map

| Data / decision | Authority | Safe UI behavior now | Missing proof / contract |
|---|---|---|---|
| Evaluation verdict and case counts | Independent Evaluation | Unavailable until authenticated BFF read model exists; component prototype only | Live signed Runtime audit producer, tenant-authenticated deployed API, stable DTO |
| Dataset revision / denominator | Evaluation dataset owner | Display only source-attested revision and aggregate counts | Immutable production dataset revision and policy-owned sample accounting |
| Signed execution evidence | Runtime signer + Evaluation verifier | Verified only if trusted source confirms the signature and binding | Production signer, key rotation/revocation, service identity, mTLS/IAM and trusted key source |
| Optimizer identity/state | GEPARD / Orchestrator | Distinguish deterministic mock from real GEPA | Real GEPA run, authorized model gateway, budgets, operation API and traceable experiment |
| Candidate identity/digest | Builder / immutable AgentSpec source | Candidate only; never assume safe/current | Authoritative version API and digest semantics |
| Release / rollback | Control Plane / AgentStore and deployment authority | Read-only unavailable until real source confirms | Live approvals, promotion, deployment, rollback and audit receipt integration |
| Permission / allowed action | BFF + owning service | Display hint only; server re-authorizes every command | Trusted actor/session, per-action scopes and tenant isolation |

Repository evidence:
- [Evaluation README](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/services/evaluation/README.md) explicitly describes an isolated component proof, not a deployed independent Evaluation API. Production identity, connected Runtime, Kafka/Langfuse, production KMS and real customer datasets are not connected.
- [Evaluation evidence snapshot](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/tests/quality-engine/EVIDENCE.md) records 117 passed / 3 skipped and 93% statement coverage locally; it says the runs used locally staged sources, not the exact current PR head. The skipped tests cover real PostgreSQL, live LiteLLM and live DSPy/GEPA.
- [GEPARD README](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/05-quality-engine/services/gepard-optimizer/README.md) says the default is deterministic mock, not DSPy GEPA.
- [Control Plane README](https://github.com/Podtverzhdeno/Agent-Factory/blob/agent/01-control-plane/services/factory-orchestrator/README.md) says default storage/approval wiring is fail-closed or mock-backed, and an AgentStore RELEASED channel does not switch a live runtime.
- [Draft integration PR #6](https://github.com/Podtverzhdeno/Agent-Factory/pull/6) describes a synthetic Runtime → signed-audit → Evaluation → mock-candidate retest. It explicitly lacks real GEPA, Java AgentStore release and production IAM/KMS/Kafka/LiteLLM proof.
- [Proposed Studio DTOs and routes](https://github.com/Podtverzhdeno/Agent-Factory/blob/design/frontend-studio-rfc-20261028/docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md) are not assertions of live endpoints.
- [AF-REQ-107/108/109](https://github.com/Podtverzhdeno/Agent-Factory/blob/design/frontend-studio-rfc-20261028/openspec/changes/studio-cjm-parallel/specs/studio-cjm/spec.md) require source-owned Evaluation status, sealed-gold protection, truthful optimizer type and source-authoritative release.

## 3. Proposed Scorecard fields

This is a mapping proposal, not a frozen TypeScript contract.

### Identity and reproducibility
- Evaluation run ID, tenant/workspace resolved from trusted server session, source reference and source revision.
- Immutable candidate AgentSpec digest and, for comparisons, immutable baseline digest.
- Dataset ID and exact revision; evaluation policy/evaluator version; runtime and tool schema revisions.
- Started/completed timestamps, source-as-of time, completeness/freshness and evidence reference.
- Every displayed datum records authority/provenance and safe source timestamp.

### Outcome and diagnostics
- Source-owned status: PASSED, FAILED, BLOCKED, INCONCLUSIVE or UNAVAILABLE. Unknown future statuses render as unsupported/unavailable, never green.
- Passed and total counts, nullable if unknown; explicitly define exclusions and denominator. Null is not zero.
- Safe aggregate finding taxonomy, for example output-schema mismatch, missing required tool, invalid tool arguments, policy denial, memory boundary violation, absent trace, invalid evidence signature, unconfirmed external effect or budget limit.
- Safety hard veto with stable reason code. One critical veto blocks promotion even if aggregate quality or price improves.
- Effect proof: NOT_REQUIRED, UNCONFIRMED, CONFIRMED_BY_EXTERNAL_RECEIPT, RECONCILIATION_REQUIRED, UNAVAILABLE, or source-approved equivalent. Never infer proof from model text, a reservation key or browser-supplied assertion.
- Latency/cost only when measured by trusted source: unit/currency, time window, sample count, denominator, p50/p95 method and attributable cost per correct business operation. Unknown billing or incomparable cohorts means unavailable, not zero.
- Holdout: safe redacted state and only policy-authorized aggregate outcomes. Never return expected answers, row content, sealed IDs or private prompt text.

### Baseline versus candidate
- Pin immutable baseline and candidate digests, prompt/harness diff and explicitly allowed change surfaces.
- Pin dataset split/revision, evaluator policy, environment, model and tool configuration.
- Show quality delta only with numerator/denominator and source-backed uncertainty method where available; never invent significance.
- Evaluate hard gates first, quality next, cost/latency second. A candidate violating a hard gate is rejected irrespective of aggregate improvement.
- Missing/insufficient evidence or incompatible samples means INCONCLUSIVE. It must not be shown as improved or equivalent.
- Every independent retest binds to the exact candidate digest; edits after retest invalidate that evidence.

## 4. Presentation state precedence

This is a UI safety rule, not a replacement for server policy.

1. **FORBIDDEN** if the current BFF denies access; clear tenant-scoped cached details.
2. **UNAVAILABLE / UNSUPPORTED** if the source is absent, too stale, or the schema/evidence verification is unknown.
3. **BLOCKED** when required signed evidence, approved gold, source inputs or prerequisites are missing.
4. **INCONCLUSIVE** when denominator, sample size or comparability is insufficient.
5. **FAILED** on source-owned failure or a mandatory safety-gate failure.
6. **PASSED** only when Evaluation returns PASSED with independently verified evidence for the pinned candidate and policy. This does not enable release by itself.

Do not recompute source-owned Evaluation verdict from chart data. Comparison calculations should be explicitly described as derived, never as an authoritative PASS.

## 5. Negative cases that must remain blocked
- Forged independentVerified flag or fabricated evidence reference.
- Signature invalid, signer expired/revoked/unknown, wrong tenant/spec/dataset/case/run ID, replay of an older run's evidence.
- Missing gold, missing required receipt, unknown denominator, incomplete/stale source or unknown status.
- Hidden holdout leakage through details, table, graph, tooltip, CSV, URL, log or error message.
- Candidate digest changed after the evaluation or approval.
- Agent text claims an ERP/payment action succeeded without an external receipt.
- Permission revoked or tenant changed while cached data remain in memory.

## 6. Request to I00/A01

Freeze a versioned DTO and typed error contract with:
- evaluationRunId, status, candidate and baseline digests, dataset revision, evaluation policy revision;
- passed / total / excluded counts with nullable semantics;
- evidence verification state and role-safe reference, hard veto/reason code, safe finding aggregates;
- effect verification and receipt reference with server-enforced redaction;
- measured metrics with units, time window and denominator; null/unreconciled is unavailable;
- source stamp, schema version, freshness and completeness;
- allowed actions as UX hints only; each mutation is re-authorized server-side;
- safe 401/403/409/429/503 and 202 receipt/polling behavior.

I00 owns shared DTOs and aliases; A01 owns server-side transport/authorization. A06 must not edit those shared paths.

## 7. Status ledger

| Item | Observed status |
|---|---|
| Issue #13 | BACKLOG / WAITING_FOR_C0; no owner or lease |
| Studio C0 / frozen BASE_SHA | Not found on checked Studio specification branch |
| Evaluation | Isolated component prototype; not deployed / no trusted live BFF |
| GEPARD | Default deterministic mock; real GEPA execution not evidenced |
| Control Plane / AgentStore | Draft mock-backed workstream; live promotion/deployment unverified |
| A06 UI implementation and tests | Not started; no C0 test harness |
| ADR-0002 | PENDING OWNER DECISION |
| This report | Proposal only, not runtime evidence |

## 8. Required I00 decisions
1. Publish exact C0 SHA, public exports, schema versions and app/test foundation.
2. Define signed-evidence authority and binding between Runtime run, candidate, dataset and Evaluation run.
3. Define freshness, schema mismatch, missing denominator and invalid/expired evidence behavior.
4. Freeze action scopes, idempotency, concurrency, 202 polling and audit receipt semantics.
5. Define which source owns RELEASED and deployment confirmation; Evaluation PASSED alone must never be enough.
6. Demonstrate server-side holdout redaction through APIs, logs, errors and exports.

No executable UI or tests are included in this pre-C0 deliverable.