# Spec-driven development process

OpenSpec is the **single canonical source of requirements**, Spec Kit supplies constitution, clarification, planning, checklist, analysis and convergence practices. Do NOT maintain duplicate, divergent specs in both frameworks.

## Cycle
1. EXPLORE real business task, alternatives, sample permissions and success criteria.
2. PROPOSE: openspec/changes/<slug>/proposal.md.
3. SPECIFY: delta requirements/specs with AF-REQ IDs and WHEN/THEN scenarios incl. negative cases.
4. DESIGN: ports, contracts, ADR, threat model, data handling and rollback.
5. PLAN: tasks linked to requirement, test and evidence.
6. IMPLEMENT: minimal vertical slice with typed contracts and security tests.
7. VERIFY: openspec validate <slug> --strict; python scripts/check_sdd.py; actual test/CI logs and independent business evaluations.
8. REVIEW via PR; leave unchecked tasks open; human approval for risky releases.
9. ARCHIVE change only after verified implementation; promote stable specs.
10. MONITOR and create new changes when deficiencies emerge.

## Setup
Install OpenSpec from https://github.com/Fission-AI/OpenSpec and run 'openspec init' on a local checkout only after inspecting existing tracked configuration; do not overwrite this scaffold. Its CLI must be separately installed and exercised to claim strict validation. Optional Spec Kit CLI from https://github.com/github/spec-kit is for extra analysis; avoid generating a second canonical spec tree.

## Release criteria
Requirement → design/ADR → implementation task → test → evidence. Negative tests for unauthorized tools, MCP injection, tenants, hidden holdout leakage, spend overrun, crash/retry and false PASS. Document status accurately: PROPOSED / IMPLEMENTED / VERIFIED / BLOCKED. Script/CLI checks prove only syntax/structure, not working business behavior.

## Language and trust
Code interfaces in English; product guidance can be Russian. Every tool invocation constrained by external policy. Data rights and operator approvals are explicit. No secrets in spec/test fixtures and no disabling failed checks to merge.
