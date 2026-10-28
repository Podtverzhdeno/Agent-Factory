# I00 — sole frontend integrator / architecture contract gate / acceptance owner

**Status:** assignment specification, not a launched coding agent. The integrator is an explicitly appointed lead/owner, not automatically an agent with permission to ratify ADR-0002 or merge main.
**Mission:** allow A01–A10 to work concurrently from one pinned base, then assemble a functioning, safe, source-backed Studio with verified E2E.

## I. Before launching feature agents (C0 — mandatory)

1. Confirm owner ratifies or explicitly constrains pending ADR-0002 topology; in absence of ratification, frontend design/unit/fixture work can proceed but topology/deployment-dependent implementation remains BLOCKED.
2. Pin a single integration base SHA after Studio RFC/OpenSpec review and compatible backend contract revisions; publish BASE_SHA and exact API schema versions.
3. Create the minimal runnable Next.js + TypeScript strict + SCSS Modules app shell at apps/studio; create top-level layouts, global styles import, env schema, 404/error boundaries, auth entry and workspace/ops route groups.
4. Publish aliases @studio/api, @studio/contracts, @studio/ui, @studio/charts, @studio/auth and versions. Provide typed error/SourceStamp/Page, exported placeholders and safe mock transport; no fake values in live routes.
5. Create reviewed routes and global nav registry, workspace/environment switcher and Ops nav entries for all 15 sections, each access-gated, with explicit unavailable/preview states.
6. Freeze the source DTO mapping and action error semantics in CJM_UI_CONTRACTS_AND_E2E.md; adapt actual backend OpenAPI schemas in I00/A01 cooperation. Approve contract changes only after versioning and security review.
7. Create local CI commands for TS typecheck, lint/Stylelint, unit + component tests and browser E2E scaffold; pin Node/pnpm versions and lockfile; refuse unexecuted green claims.
8. Validate that all Axx work packets have truly disjoint path ownership with WORK_OWNERSHIP_MANIFEST.json and path-check script; avoid shared folder writes and parent layout edits.
9. Spawn feature agents only from C0 SHA; each receives **its specific packet** and shared docs, not an unconstrained “build frontend” prompt.

## II. Exclusive ownership

I00 owns **all paths not exclusively delegated** under docs/frontend/parallel/README.md, notably:
- apps/studio/package.json, package lock, tsconfig, Next config, app root/route layouts and route navigation registry.
- public shared generated contracts and aliases; compile/package bootstrap, auth provider wiring, top-level PageShell composition.
- tests/studio-e2e/** and security/perf/visual integration harness.
- any central CI workflow updates, script/config linting, CODEOWNERS, dependency governance.
- docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md and openspec/changes/studio-cjm-parallel/**.
- integration branch, final cross-PR merge and last-mile API adapter coordination with backend owners.

**Not I00 rights:** unilateral owner ratification of ADR-0002, production access/secret exfiltration, policy bypass, or release of unsafe agent. I00 cannot claim production without owner acceptance.

## III. Per-PR intake quality gate (before integration)

- Path allowlist check: no unowned changes, generated contracts, root package, configs, layouts, service code or E2E folder changes.
- Review all new imports and package requests; no direct feature→feature internal imports or circular references; no unsafe any/no blanket ignore to hide errors.
- Request/response DTO compatibility with frozen version and real backend API; no invented accepted status or false PASS.
- Security: wrong role, other tenant, unavailable service, expired file link, hidden gold and forged evidence negative tests.
- Screen-level UX: loading/empty/stale/partial/no permission/error states, screen reader/keyboard, responsive SCSS and source provenance.
- Actual test results on exact commit, fixture source and skipped test reasons; screenshot-only or docs CI never counts as E2E.
- CONTRACT_CHANGE_REQUEST / DEPENDENCY_REQUEST is reviewed and merged centrally as a separate commit before dependent feature PR is retested.

## IV. Merge / integration sequence

**Never merge all ten PRs untested or cherry-pick isolated pieces with silent conflicts.**

0. C0 single base; collect typed fixture expectations from all teams. Platform A01 and UI A02 produce public exports first. If aliases/contracts move, issue a versioned freeze update to everyone.
1. Merge A01 + A02 into temporary integration branch. Run app build, auth route negative suites, source availability, shared component and chart tests. Record SHA.
2. Merge A03 + A04 (Task + Agents/Workflow). Run real/synthetic READY snapshot → build status, 401/403/409, double-click, stale refresh. Record SHA.
3. Merge A05 (Runtime/Run) and A06 (Quality/Versions). Run signed audit/effect-receipt negatives, independent Evaluation, GEPARD mock-vs-live truth, release/rollback denial tests. Record SHA.
4. Merge Ops A07 + A08 + A09. Verify **exactly 15 routes**, 15 capability IDs, correct 5/5/5 ownership, source unavailable behavior, cross-tenant ops privileges, chart provenance.
5. Merge A10. Verify bilateral design behavior and consent-denied privacy in synthetic fixtures. Keep live A/B creation disabled until real double-tenant backend and joint evidence gates pass.
6. Execute **all 24 CJM-E2E scenarios** and two distinct factory acceptance fixtures on ONE pinned integrated revision; document test types: unit, component, mock-backed browser, real staging service, production; do not collapse results.
7. If full backend integration unavailable, mark precise blockers and release only non-deceptive pilot UI states. Do not change CI to make a blocked integration pass.

## V. Recommended integration test layers

**T1 — structure:** path owner script, source contract schema, TS strict and SCSS lint, dependency licensing/security, forbidden import check.

**T2 — component:** per-feature happy/error/stale/blocked states, keyboard and ARIA. Synthetic fixtures isolated/clearly tagged.

**T3 — UI mock E2E:** all critical navigation and actions under mock BFF using tenant A/B identities. Cover 401/403/409/429/503, quota, file rights, repeat commands and unknown enum.

**T4 — real integrated service:** approved Task Intake → Registry → Builder → sandbox Runtime → signed independent Evaluation, actual GEPARD candidate/retest if connected, LiteLLM budget and Control Plane gate; use **RFQ and certificate verification** and negative effect receipt tests.

**T5 — bilateral advanced:** two synthetic authorized tenants, two BTPs, A/B official A2A transport and 3 independent metrics, A0×B0 vs cross-play matrices; partner data isolation and consent revocation. NO production claim before real deployment.

**T6 — ops/scale:** 15 section auth+availability, verified chart source completeness, large trace pagination, reconnect surge only when SSE deployed; never invent workload/throughput numbers. Record actual result and bottleneck.

## VI. Go/no-go for each feature

Use 4 levels:
- DESIGN ONLY — spec and fixtures; no working backend claim.
- COMPONENT VERIFIED — local code/tests, no integrated service proof.
- STAGING VERIFIED — real cross-service browser test, evidence SHA+dataset version.
- PRODUCTION VERIFIED — owner approved deployed artifact, IAM/keys, effect proofs, release/rollback and operational telemetry.

A service failing a hard veto or lacking real production effect receipt is not promoted due to a green browser mock or synthetic signed test. Operator modules can be visibly planned/unavailable while scope remains mandatory.

## VII. Test evidence ledger template

| Req ID | Work packet / PR | Integration SHA | API/dataset version | Command | Actual result | Negative/security | Remaining blocker | Reviewer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AF-REQ-100 | A01 PR TBD | TBD | TBD | NOT RUN | NOT RUN | other-tenant cache | IAM / C0 | I00 |
| AF-REQ-112 | A07–A09 PRs TBD | TBD | TBD | NOT RUN | NOT RUN | Ops route 403 | 15 source adapters | I00 |
| AF-REQ-116 | A10 PR TBD | TBD | TBD | NOT RUN | NOT RUN | B consent missing | bilateral E2E | I00 |

Every row stays OPEN until specific artifacts and results replace placeholders.

## VIII. Agent dispatch command template

Paste the following to EACH isolated agent and add its Axx work packet:

> Implement only docs/frontend/parallel/Axx_*.md against I00-specified BASE_SHA. Read AGENTS.md, openspec/changes/studio-cjm-parallel, docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md and CJM_UI_CONTRACTS_AND_E2E.md. Your only write scope is the exclusive allowlist in Axx. Do not alter Java/Python services, ADR, root manifests, Next layouts, global OpenSpec, shared DTOs or another workstream. Build source-safe UI with SCSS Modules, strict TS, fixture tests, permission/error/degraded states; never fake live service readiness, PASS or RELEASED. If you need a cross-team change, write a feature-local request for I00. Provide PR, file diff, actual test evidence, blockers and no merge to main.

The dispatch is only valid after C0. The fact that a GitHub work packet exists does NOT mean autonomous agents are running.