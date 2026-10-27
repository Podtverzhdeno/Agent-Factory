# Five independent coding agents — execution pack v0.1

**Status:** task decomposition is ready. The repository currently contains specifications, not a working MVP. Service deployment topology is still **DRAFT** until the owner personally ratifies ADR-0002 via a traceable GitHub action. Never treat this pack as that approval.

## Launch model

Run five independent coding agents, **one branch/worktree per agent**. Read `AGENTS.md`, `docs/product/MVP.md`, `docs/parallel/CONTRACTS_V0.md`, then only the assigned task file. Branches are created from the same frozen SDD foundation commit, not from each other's branches.

| Agent | Branch | Sole write ownership | Work packet |
| --- | --- | --- | --- |
| 01 Control Plane | `agent/01-control-plane` | `services/factory-orchestrator/**`, `services/agent-store/**`, `tests/control-plane/**` | [01](agents/01-control-plane.md) |
| 02 Business Task | `agent/02-business-task` | `services/business-task/**`, `services/document-ingestion/**`, `tests/business-task/**` | [02](agents/02-business-task.md) |
| 03 Tool Registry | `agent/03-tool-registry` | `services/tool-mcp-registry/**`, `tests/tool-registry/**` | [03](agents/03-tool-registry.md) |
| 04 Agent Engine | `agent/04-agent-engine` | `services/agent-builder/**`, `services/agent-runtime/**`, `services/litellm-adapter/**`, `tests/agent-engine/**` | [04](agents/04-agent-engine.md) |
| 05 Quality Engine | `agent/05-quality-engine` | `services/evaluation/**`, `services/gepard-optimizer/**`, `tests/quality-engine/**` | [05](agents/05-quality-engine.md) |

**The ownership unit is a developer's work packet, not necessarily a single deployed microservice.** This is intentional: five parallel workers cover the whole single-agent MVP. A deployable count is an ADR decision. Supporting services, e.g. Soup fine-tuning or bilateral A2A, are NOT MVP coding assignments in this wave. The shared LiteLLM Proxy is selected by the owner, but independent proxy deployment/infrastructure changes are NOT owned by workstream 04; workstream 04 owns its typed client adapter and can test against a mock.

## Frozen shared interfaces

[CONTRACTS_V0.md](CONTRACTS_V0.md) is the preliminary integration agreement. **READ-ONLY for all five agents.** Use mocks/ports for other services. Proposed interfaces are pending owner ratification; use experimental contracts and avoid hard-coding final deployment topology.

If a contract is missing or incompatible, submit a change proposal in **your own** `services/<owned>/CONTRACT_CHANGE_REQUEST.md` (or PR description), stating example payloads and compatibility implications. Do not edit shared files or a colleague's service.

## Start instructions

1. Assign five separate sessions/worktrees using the branches shown above.
2. Paste each work packet's **Copy/paste launch prompt** into the corresponding coding agent.
3. In each branch implement only the owned code/fixtures/tests; where ADR-0002 blocks service-boundary implementation, produce typed contract-first stubs and executable component tests and mark the remaining implementation **BLOCKED**, not complete.
4. Every agent opens a PR targeted to `docs/sdd-foundation-mvp` (temporary integration base) for review. Once the foundation is approved/merged into `main`, coordinate PR rebases and retargeting; never self-merge.
5. Run each workstream's local tests in isolation, then owner/integrator runs [integration gate](INTEGRATION_GATE.md).

## Guardrails

- No edits to root `README.md`, `AGENTS.md`, shared `openspec/**`, `.github/**`, `docs/architecture/**`, `docs/product/**`, `docs/parallel/**`, or another agent's paths. Current OpenSpec is canonical, reference AF-REQ IDs in owned tests and PR description.
- Respect architecture owner decision gate `T00`: agents may prepare contracts, fixtures, mock-backed components and options, but cannot declare proposed service boundaries ACCEPTED or silently bypass governance.
- Each bounded context owns its data/migrations. No cross-database reads or cross-tenant secrets.
- Use safe synthetic fixtures only. No generated live orders/payments/irreversible effects.
- One agent's PR is not proof the others work; never report factory MVP as verified until E2E.

## Single-agent MVP priority

One specialized corporate agent: input files + business requirements -> trusted tool selection -> build AgentSpec -> Python/LangGraph runtime -> independent Evaluation -> bounded GEPARD -> quality gate -> versioned AgentStore. A2A endpoint supported; two-organization paired optimization optional and excluded from first wave.
