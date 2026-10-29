# A06 — Version, Release and Rollback Authority Matrix

**Status: PRE-C0 RESEARCH ONLY. No executable UI or release action.** Task STU-T08 / Issue #13. No C0 SHA or task lease has been granted to A06.

## Keep lifecycle states separate

| Concept | Authority | Preconditions | Does not imply |
|---|---|---|---|
| CANDIDATE | Builder / immutable AgentSpec source | Candidate digest and revision exist | Tested or active |
| VERIFIED | Independent Evaluation plus release policy | Trusted evidence on exact digest and required hard gates pass | Released or deployed |
| RELEASED | Control Plane / AgentStore release policy as defined by owner contract | Actor authorization, approvals, exact version and confirmed source result | Evaluation PASS or HTTP 202 |
| ROLLED_BACK | Control Plane / AgentStore plus deployment authority when separate | Authorized target digest, confirmed transition and audit evidence | Button click, accepted request or old version listing |

If registry publication and deployment are separate actions, keep promotion and deployment as distinct fields. The word RELEASED must follow the approved source contract. Never call a version active in runtime without evidence of the deployed target.

## Release decision matrix

| Condition | UX / behavior | Response example | Recovery |
|---|---|---|---|
| Missing/expired session | No mutation; re-authenticate | 401 | Reload trusted status and clear actor-bound cache |
| Wrong tenant / view denied | Forbidden without existence leak | 403 | Request authorized access; do not retry write |
| Missing release scope | Hide/disable UI action; server also denies direct call | 403 | Obtain scope from authorized administrator |
| Evaluation missing/failed/blocked/inconclusive | Preserve prior release; block command | Typed domain gate or 409 | Fix prerequisite and retest exact digest |
| Invalid/replayed signature or wrong digest | Block and audit security finding | Typed evidence rejection | Obtain trusted evidence; investigate replay |
| Candidate changes after review/approval | Mark stale; do not reuse approval | 409 | Reload and re-evaluate/re-approve changed digest |
| Approval missing/expired/revoked | Approval required / unavailable | 403/409 or source-specific gate | Obtain current authorized approval |
| Deployment target missing/unhealthy | Read-only unavailable; no release badge | 503 or typed dependency state | Restore via target owner |
| Request accepted asynchronously | Pending confirmation | 202 | Poll the original operation receipt |
| Timeout/lost response | Status unknown, reconcile original operation | timeout/5xx | Query by stable receipt/idempotency key; no blind duplicate |
| Confirmed release response | Show source-owned state and audit ref | Terminal source receipt | Refresh authoritative release/deployment view |
| Rollback target missing/incompatible/stale | Reject; current version stays active | 403/409/domain error | Reload eligibility and history |
| Rollback accepted without deployment proof | Pending/reconciliation required | 202 | Poll release and deployment authorities |
| Confirmed rollback to pinned target | Show ROLLED_BACK and target digest | Terminal receipt | Preserve append-only transition history |
| Unknown schema/state | Unsupported/unavailable | Contract-defined 409/503 | Retry only as source directs; otherwise escalate |

The codes above are proposed UX semantics, not a claim that all upstream routes already implement them. I00/A01 must freeze exact payloads and retry semantics.

## Mandatory command invariants

Every release/rollback command must be explicitly user-initiated, scoped to trusted tenant/session/environment, pinned to version digest and expected revision, idempotent, permission-checked by server, protected by required independent Evaluation and approvals, and followed by a source-authored audit receipt. The confirmation view must identify agent, candidate/target digest, environment, safety findings and approvals. Client flags are never authorization.

A 202 means pending, not success. If a response is lost after a possible mutation, reconcile the original operation before any retry. On partial failure, preserve both the source receipt and observed deployment state. Do not claim exactly-once effects or erase prior history.

## Current upstream limitations

- Control Plane README on agent/01-control-plane describes mock-backed state and in-memory default adapters; approvals and auto-promotion are fail-closed by default.
- That README says changing AgentStore RELEASED does not automatically switch a live Python agent.
- Draft PR #5 notes full Maven/Spring/JWT/PostgreSQL acceptance on its exact head and real 04/05 interoperability are not yet verified.
- Draft PR #6 is a synthetic Python integration and explicitly lacks Java Control Plane/AgentStore release.
- ADR-0002 remains PENDING OWNER DECISION.

## Questions for owner / I00

1. Is RELEASED intended to mean registry publication only or confirmed runtime activation? Recommendation: expose separate promotion and deployment states either way.
2. Which component is authoritative for deployed version, and what exact receipt closes the release?
3. Which risk levels may auto-promote after independent retest; which always require maker-checker approval?
4. What confirms rollback if AgentStore and runtime deployment are separate authorities?
5. How do approvals bind to exact candidate digest, environment and expected revision, and how is revocation checked?

No release or rollback endpoint was invoked; no source-owned release state was changed.