# Change: studio-cjm-parallel

## Why

Agent Factory needs a truthful, role-scoped frontend following a real client journey across Task Intake, Builder, Runtime, independent Evaluation, GEPARD, AgentStore and authorized A2A rather than a collection of disconnected microservice dashboards. User additionally requires a complete 15-section Operator Console, an extensive source-backed chart library and an advanced two-enterprise collaborative build journey. Parallel coding agents need non-overlapping file ownership, contract freeze and an independent integration gate.

## What changes

- Define end-to-end customer and operator journeys with screen, state, action, source, error and accessibility contracts.
- Define a server-authoritative Studio BFF read/action model with derived tenant/role/capability availability, typed DTOs, idempotent commands, safe files and verified evidence.
- Specify mandatory 15 operator sections, chart library, and advanced bilateral buyer/supplier UI with separate authorization and releases.
- Keep LangGraph visual editor and microfrontend decomposition as **ideas only, no implementation**.
- Provide ten mutually isolated parallel frontend work packets and an integrator-only contract/merge/test track.
- Require traceability from requirement → task → test → actual evidence.

## Non-goals

Ratification of unapproved ADR-0002; new Java/Python service topology; implementation/deployment by this documentation change; promises of working Task Intake, live GEPARD, external effect receipt, A2A payments, Module Federation or graph editing; exposing customer gold, secrets or cross-tenant data in the browser.

## User scope decisions

Single-company specialized agent remains first pilot vertical slice. Full operator console and typed chart kit are mandatory **target boxed product** modules and must be designed now; their integration can be progressive and cannot show fabricated data. Two-company builder is a committed advanced scenario requiring real bilateral backend E2E. Editor/microfrontends are future ideas only.

## Architecture constraints

Browser → Next.js Studio/BFF → authenticated service APIs. Service-owned databases and state transitions remain authoritative. Existing contracts in docs/parallel/CONTRACTS_V0.md are read-only. ADR-0002 requires owner's own ratification before topology-dependent implementation.

## Acceptance

Same generic factory creates RFQ and certificate agents from distinct BTPs, correct sandbox artifact and signed independent Evaluation (or accurate BLOCKED); UI reflects exact status. No false PASS/RELEASED, no cross-tenant access, unknown states safe, no secret/holdout leak, real operator diagnostics and chart provenance; synthetic and staged bilateral tests separated from production claims. All frontend features must be supported by executable tests on one integrated revision.

## References

- docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md
- docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md
- docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md
- docs/frontend/STUDIO_CAPABILITY_API_CONTRACT.md
- docs/frontend/parallel/README.md


## Additional live parallel work coordination (2026-10-28)

The owner requests a trustworthy visible activity trail per task (who claimed, when, last status/progress and linked PR), a two-hour inactivity rule and safe reassignment when no free tasks exist. Add AF-REQ-126..131 and STU-T19..23; see docs/frontend/parallel/TASK_LEASE_PROTOCOL.md. A stale status is a review signal, not proof the previous agent abandoned work; a serialized lease coordinator and generation fencing prevent duplicate owners.
