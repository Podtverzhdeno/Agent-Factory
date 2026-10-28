# Tasks: studio-cjm-parallel

**ALL implementation work OPEN.** Spec-writing creates no implemented UI. Architecture topology requiring ADR-0002 remains blocked pending the owner's verifiable ratification.

## Setup and contract gate

- [ ] STU-T00 — Owner ratifies ADR-0002, Task Intake deployable ownership, identity/BFF and acceptable release topology (AF-REQ-124/125).
- [ ] STU-T01 — Integrator freezes proposed BFF DTOs/API schema, OpenAPI compatibility and tenant-role permission matrix (AF-REQ-100/121/122). Test CJM-E2E-006,018,022. No cross-agent changes.
- [ ] STU-T02 — Integrator provisions single pinned integration base, strict TS/SCSS, CI checks, mock server fixtures and browser test host (AF-REQ-124/125). Test path-allowlist and build, no TODO fixtures posing as live.

## Ten independent coding workstreams (see docs/frontend/parallel/README.md)

- [ ] STU-T03 — A01: shell, auth, effective features, BFF typed ports, safe async/provenance (AF-REQ-100/110/121/122). Test CJM-E2E-006/018/022.
- [ ] STU-T04 — A02: shared UI / SCSS Modules / 15 typed ChartKit templates with accessible tables and source gates (AF-REQ-114/115/123). Test CJM-E2E-013/016/023.
- [ ] STU-T05 — A03: wizard BTP and file/consent/preflight UX (AF-REQ-101..104). Test CJM-E2E-001/005/007.
- [ ] STU-T06 — A04: agents catalogue, Mission Control and workflow timeline with exact state and recovery (AF-REQ-105/110/111). Test CJM-E2E-008/021/022.
- [ ] STU-T07 — A05: sandbox playground and Run inspector (AF-REQ-106). Test CJM-E2E-002/004/016.
- [ ] STU-T08 — A06: independent Quality, GEPARD, versions, approvals and rollback (AF-REQ-107/108/109). Test CJM-E2E-003/009/010/011/024.
- [ ] STU-T09 — A07: Ops fleet/workflows/builder/runtime/registry (AF-REQ-112/113). Test ops route subset + forbidden mutation.
- [ ] STU-T10 — A08: Ops connectors/artifacts/evaluation/gepard/models (AF-REQ-112/113/114). Test model data unknown and source outage.
- [ ] STU-T11 — A09: Ops a2a/releases/observability/security/incidents (AF-REQ-112/113/115). Test audit/tenant/mutation privileges.
- [ ] STU-T12 — A10: advanced bilateral UX, invitations, A/B independent disclosure and cross-play (AF-REQ-116/117/118). Test CJM-E2E-014/015.
- [ ] STU-T13 — Integrator docs-only idea preservation for LangGraph editor and microfrontends; **no coding** (AF-REQ-119/120). Test CJM-E2E-017.

## Integration and validation

- [ ] STU-T14 — Integrator collects ten isolated PRs from identical base, validates file allowlists, contract change requests and API schema diffs; composes common root routes and imports (AF-REQ-124).
- [ ] STU-T15 — CI executes actual TS/SCSS lint, unit, component, OpenAPI checks, Playwright E2E on one merged pinned SHA, security and accessibility negative suites (AF-REQ-125); attach commands/log links and versions.
- [ ] STU-T16 — Independently validate live Task Intake/Registry→Builder/Runtime→Eval/GEPARD/AgentStore/LiteLLM/A2A bridges as available. Do not mark service missing as passing.
- [ ] STU-T17 — Verify two distinct business fixtures (chemical RFQ and certificate) and blocked/false-effect tests, bilateral synthetic experiment separately.
- [ ] STU-T18 — Owner acceptance, rollback/release policy, user trial against real business scenarios, signed ADR when required; record unsupported capabilities and actual current availability.

## Requirement / test mapping

AF-REQ-100→CJM-E2E-006/018; 101→007; 102→001/007; 103→005; 104→001; 105→008/021; 106→004/016; 107→003/004/009; 108→003/024; 109→010/011; 110→021/022; 111→001/002; 112→012; 113→012/020; 114→013/019; 115→006/016; 116→014/015; 117→015; 118→014; 119/120→017; 121→009/017; 122→009; 123→023; 124→path-allowlist integration check; 125→all CJM-E2E suite.

Evidence record per task: requirement ID, agent PR, SHA, API schema version, fixture/dataset revision, test command and **actual** output, security finding, reviewer, remaining blockers. Do not check off or claim E2E while tests are not executed.
