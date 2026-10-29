# A06 pre-C0 research: contract gaps and implementation gates

**Status: design/research only; no executable feature code, no claim and no lease.**  
Task: STU-T08 / [Issue #13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13).  
Reviewed C0-R evidence: [PR #20](https://github.com/Podtverzhdeno/Agent-Factory/pull/20), head `e5a39cd95186be0804673b186fc812d1f5de9ab1`. That is a reproducible foundation on a Draft branch, not a frozen shared BASE_SHA or permission to code.

## 1. Evidence boundary

The checked C0-R contract files are proposals, not assertions of deployed APIs:

- `apps/studio/src/contracts/index.ts` at `387fd2e4b449b4d0d233c2c36960708c3ae7d3f8` defines `SourceStamp`, `SafeError`, `FeatureAvailability`, and re-exports `EvaluationView`; the file itself calls the models proposed and not confirmed deployed APIs.
- `apps/studio/src/contracts/view-models.ts` at `278f37294b70cbf04842b987057c2238db75d34e` includes an `EvaluationView`, but no typed GEPARD experiment, immutable version, approval, release-command receipt or deployment-observation model.
- The common stamp carries source, source time, completeness and revision. This is useful but does not by itself prove the signer, authorization or binding of an evidence artifact.
- Expected public BFF/transport entrypoints `apps/studio/src/shared/api/index.ts` and `apps/studio/src/server/index.ts` did not resolve at the reviewed C0-R ref. Do not infer that the browser can call Java/Python services directly.

The exact open requirements are AF-REQ-107 (independent Evaluation), AF-REQ-108 (governed optimization), and AF-REQ-109 (source-authoritative version/release/rollback). They require truthful evidence, immutable baseline/candidate hashes, independent retest and real release/rollback source state. The canonical acceptance targets are CJM-E2E-003/004/009/010/011/024.

## 2. Gaps against the C0-R DTO surface

| A06 capability | Existing C0-R surface | Gap before a contract can be frozen |
|---|---|---|
| Evaluation | `EvaluationView`: run ID, candidate digest, dataset revision, status, `independentVerified: boolean`, evidence ref, required-effects boolean and passed/total counts | Replace a free boolean with a source-owned verification envelope bound to exact run/spec/dataset/tenant and verifier result; add evaluator/policy revision, baseline digest, excluded count/denominator definition, hard safety veto/reason taxonomy, safe finding aggregates, evidence freshness, source/signer metadata, and provenance-aware cost/latency only when available. |
| GEPARD | No typed experiment/candidate view in `view-models.ts` | Versioned record for durable experiment/operation ID, honest backend identity (MOCK vs verified real backend), baseline/candidate/patch digests, allowed changed surface, attempt/deadline/budget cap vs actual usage, non-holdout tuning/validation refs, independent retest run bound to the exact candidate digest, and safe terminal/pending/error states. |
| Versions | `AgentSummary` has candidate/released digest fields but is not a version history | Immutable version identity/revision, source provenance, compatibility, active/published state and lifecycle history. A candidate digest alone is not a release record. |
| Release and rollback | `ActionDescriptor` describes allowed/confirmation/approval flags; `WorkflowView.pendingOperationId` is generic | Release eligibility with server reason; approval identity/scope/expiry and required count; expected source revision; target environment; idempotency/operation receipt; audit ref; and a separate deployment observation when publication and runtime activation differ. |
| Authorization / transport | Proposed common `SafeError` and `FeatureAvailability`; no verified public A06 BFF route at reviewed ref | A01/I00 must own authenticated tenant-scoped transport and validate untrusted JSON. UI flags are advisory; each mutation is independently authorized server-side. Freeze stable 401/403/409/429/503 and asynchronous 202 semantics. |

**Specific contract recommendation:** avoid making `independentVerified` a caller-settable assertion. Prefer a source-issued envelope with at least `verificationState`, `verifiedAt`, verifier/source revision, and exact run/spec/dataset/tenant binding. Public UI should see only a role-safe signer/key reference, never private key material or hidden holdout information.

These gaps describe the reviewed C0-R surface and the evidence checked so far; they are not a claim that no other branch contains partial prototypes. Any discovered source must be inspected at its exact SHA and validated for live deployment before marking a capability connected.

## 3. Route-level state contract (proposed)

| A06 surface | Required states | The UI must never infer |
|---|---|---|
| Agent Quality / Scorecard | loading; empty; source-unavailable; stale/partial; forbidden; blocked; inconclusive; failed; passed with verified provenance | PASS from a fixture, missing data as zero, or Evaluation PASS as release approval |
| GEPARD experiments / candidate diff | empty; queued/running with durable operation ID; candidate proposed; retest required/running; accepted-for-release-review; rejected; blocked; inconclusive; unavailable; stale | real GEPA from a mock adapter, improvement from optimizer prose, or promotion from a retest alone |
| Agent versions | source-backed immutable history; candidate; verified; released; rolled back; unavailable/unsupported; stale | that a candidate is tested, that a version label is the current runtime, or that a registry write changes a running deployment |
| Release / rollback | eligibility; approval required; forbidden; stale revision; pending; confirmed; failed; unknown/reconciliation required; unavailable | success from button click, HTTP 202, timeout, a cached status, or a successful promotion without deployment proof |

In local tests, fixture-backed states must be visibly marked DEMO/TEST. In the product, missing or untrusted sources render unavailable/blocked and privileged actions remain disabled; do not simulate operational success.

## 4. Required negative and concurrency tests

1. Forged `independentVerified`, invented evidence ref, signature failure/replay, wrong tenant/run/spec/dataset or expired key cannot produce PASSED.
2. Missing gold, insufficient denominator or incompatible baseline/candidate cohorts yields BLOCKED/INCONCLUSIVE/UNAVAILABLE—not green, zero spend, or “no regression”.
3. Sealed holdout rows, gold answers, hidden IDs or private prompts never appear in DOM, URL, logs, export, tooltip or exception text.
4. Mock GEPARD is visibly mock; a hard-gate regression rejects candidate regardless of average score/cost; editing its digest invalidates the retest.
5. Repeated command with the same idempotency scope does not create a second semantic operation; a lost 202/timeout reconciles the original receipt rather than blindly retrying.
6. Missing/expired approval, 403, stale revision/409, source outage/503 and unsupported state never produce a release badge.
7. Rollback accepted but deployment unconfirmed remains pending/reconciliation-required; history is append-only.
8. Tenant switch/revoked grant clears actor/tenant-bound data and leaves no prior-tenant payload visible.

Map automated coverage to CJM-E2E-003 (fail → bounded candidate → independent retest), -004 (missing external receipt), -009 (evaluator outage/unknown state), -010/-011 (approval and release/rollback authorization), and -024 (release/rollback recovery). A green shell build or pure/mock coordinator suite does not prove these A06 tests.

## 5. Decision requests to I00 / A01 / service owners

1. Publish versioned public DTOs and fixture examples for Evaluation, optimizer operation/candidate, immutable version, approval, release receipt and deployment observation; include freshness/completeness and typed unknown-state handling.
2. Confirm the source of truth for `RELEASED`: AgentStore publication or deployment confirmed. If publication only, expose deployment independently; do not label the version active without deployment evidence.
3. Define the signed-evidence verification result and its exact binding. The browser must not be the verifier or policy authority.
4. Define command retry/reconciliation semantics and stable operation/receipt IDs for 202, timeouts and partial failure.
5. Keep optimizer identity honest: deterministic mock and fake DSPy contract test are not real GEPA; document the evidence required to call the backend real.
6. Freeze and publish the single C0 BASE_SHA, contract package exports and route ownership. Separately, activate the trusted task coordinator and grant STU-T08 a generation-fenced lease before starting executable feature work.

## 6. Proposed execution sequence after authorization

1. I00 freezes C0 and public exports; task coordinator verifies actor identity, path rights and BASE_SHA and grants the task lease.
2. A06 implements only the owned feature/routes against validated, explicitly synthetic fixtures for unavailable capabilities; tests all local states and negative cases.
3. A01/service owners connect typed BFF adapters to exact versioned source contracts; live features are enabled only with verified source and permission evidence.
4. I00 runs the required integrated browser/E2E suite on one pinned SHA. A06 does not claim integrated E2E or production release acceptance by itself.

**Current conclusion:** C0-R reduces the build-foundation uncertainty, but the A06 typed service contracts, trusted evidence semantics, live coordinator and frozen C0/lease gates remain open. This report is a dependency handoff, not implementation or authorization.
