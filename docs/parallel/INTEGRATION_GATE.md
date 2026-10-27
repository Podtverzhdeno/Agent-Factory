# Integration Gate — five independently developed workstreams

This checklist is owned by the human integrator/architecture owner, NOT by one of the five coding agents.

## Before starting

- [ ] Owner reviews \`docs/parallel/CONTRACTS_V0.md\` and five work packets; signed ADR-0002 is still required to ratify topology/deployment decisions. Do NOT claim service topology accepted from this coordinator-authored spec.
- [ ] Each agent starts from the SAME foundation commit in its own branch/worktree.
- [ ] All five agents agree to their path allowlist and read-only shared OpenSpec/contracts. No cross-agent writes.
- [ ] Each agent can test its work with mocked required neighbor interfaces and synthetic business fixtures.

## Per-PR intake

For each of the five PRs require:
1. Change set strictly within that agent's exclusive owned paths (beyond generated lockfiles placed in that module).
2. API examples matching \`CONTRACTS_V0.md\`; any deviations documented as CONTRACT_CHANGE_REQUEST, no silent schema drift.
3. Requirement IDs and task IDs linked to unit/integration tests and **actual executed** output. A green spec check alone is insufficient.
4. Negative security tests (unauthorized tenant, unsafe tools, false PASS, missing files, cost caps, storage isolation where applicable).
5. No hardcoded provider keys; no private customer datasets; no real irreversible operations.
6. Failures listed honestly; don't mark README/architecture status as implemented prematurely.

## Integration sequencing (not development dependency)

**Contracts and mocks let all agents work in parallel.** Integration is ordered for deterministic troubleshooting:

1. Task Intake -> Orchestrator READY snapshot acceptance: schema, tenant, immutable revision.
2. Tool Registry -> Builder capability lookup: approved tool versions, missing-scope and no-match blockers.
3. Builder -> Runtime: AgentSpec validation, environment/secret separation, typed graph and memory.
4. Runtime -> Evaluation: submit a task to a sandbox agent, verify output artifact, real tool-effect proof and trace.
5. Evaluation -> Orchestrator -> GEPARD -> Evaluation: fail -> candidate prompt -> independent retest -> gate.
6. Orchestrator -> AgentStore: release only verified pinned AgentSpec and allow rollback.
7. LiteLLM mock -> configured proxy: model allowlists, separate tenant budget accounting, provider faults. Never claim infra integrated until tested.
8. A2A external client -> released Runtime: positive protocol compatibility and unauthorized negative case.

## Required end-to-end acceptance

Run **both** approved B2B fixtures:
- Chemical RFQ request -> catalog lookup -> valid quotation draft with provenance, no live order/payment.
- Supplier/certificate check -> permitted document/source verification -> auditable discrepancy report, no fabricated certificate verification.

Both must be built by the same Builder implementation from two different BTP/Tool configurations without changing factory source between runs. Inject a known bad tool description or prompt and demonstrate diagnosed improvement OR correct explicit BLOCKED when allowed repairs cannot help.

Quality hard gates: no unauthorized tool, no hidden-holdout leakage, no false PASS, no cross-tenant memory read, no duplicate irreversible effect after restart. Model savings may return INCONCLUSIVE if evidence cannot prove quality non-inferiority.

## Merge policy

- The foundation PR #1 is currently not in \`main\`. Until merged, workstream PRs target \`docs/sdd-foundation-mvp\`; avoid merging experimental service code into an unapproved architecture branch.
- In human integration: first approve/finalize ADR, review each PR, then run whole-app E2E on one integration head. Retarget/rebase onto main after the foundation is merged, resolving schema conflicts explicitly.
- No agent autonomously merges PRs or rewrites other agents' branches.
- Project status stays \`SPEC ONLY / PARTIAL\` until executable E2E evidence exists.

## Out-of-scope wave 1

Two-enterprise joint agent factory, cross-organization A2A simulation, Soup training, Pi Durable PoC, public AgentStore marketplace and Kubernetes scaling. Those remain documented optional stages, not blockers to one-agent factory MVP.
