# Agent Factory

**Verified Self-Optimizing Agent Factory** — a research-first platform that converts a specific B2B task into the smallest capable agent, tests it, diagnoses failures, improves its approved configuration and publishes only verified versions.

> Status: **SDD / specification bootstrap**. No runtime, production integrations or customer-ready agents are implemented.

## MVP target

Business task + measurable acceptance criteria → trusted capability selection → minimal Agent Spec → sandbox execution → evaluation → bounded repair / GEPARD optimization → release gate → versioned deployable artifact with A2A interface.

**Pilot demonstration:** two distinct procurement-related tasks assembled from one core using different approved tools, with no changes to the factory's source code between builds. At least one failure is diagnosed, repaired and re-evaluated. An impossible/unsafe task must end as BLOCKED, not falsely PASSED.

## Engineering process

- Canonical requirements and changes: [OpenSpec](https://github.com/Fission-AI/OpenSpec) under [openspec/](openspec/).
- Engineering constitution, gates and planning methodology inspired by [Spec Kit](https://github.com/github/spec-kit): [.specify/memory/constitution.md](.specify/memory/constitution.md).
- Working agreement: [AGENTS.md](AGENTS.md) and [SDD workflow](docs/process/SDD.md).
- Product scope: [docs/product/MVP.md](docs/product/MVP.md).
- File-backed, typed business requirements: [Business Task Package RFC](docs/architecture/BUSINESS_TASK_PACKAGE_RFC.md) (owner review pending).
- Microservices (**style selected by owner; topology not yet approved**): [architectural questions](docs/architecture/OWNER_QUESTIONNAIRE.md), [owner ADR](docs/architecture/adr/0002-microservices.md), [logical architecture](docs/architecture/architecture.md).
- Current proposed change: [bootstrap-factory-mvp](openspec/changes/bootstrap-factory-mvp/).

## Developer setup for specifications

1. Install [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) and run: openspec validate bootstrap-factory-mvp --strict
2. Run local repository checks: python scripts/check_sdd.py
3. Optional: install [Spec Kit specify-cli](https://github.com/github/spec-kit) to use its clarification, checklist, analysis and convergence techniques. Do not generate a second competing set of canonical requirements.
4. Run the real implementation test suite once implementation exists. This repository currently contains **specification only**.

See [quality gates](docs/quality/gates.md) before any feature or release PR.

## Milestone sequence

M0 — reviewed SDD → M1 — Task Contract and Registry → M2 — assembly and sandbox run → M3 — evaluators and bounded repairs → M4 — GEPARD + durable restart test → M5 — independent A2A invocation and pilot evidence.

Soup/LoRA is an **optional experiment**, not a prerequisite for completing M1–M5.
