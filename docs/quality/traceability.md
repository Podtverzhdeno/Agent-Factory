# MVP requirement traceability

All values below are PLANNED, not implemented.

| Requirements | Tasks | Acceptance evidence |
| --- | --- | --- |
| AF-REQ-001, AF-REQ-002 | T01 | typed task validation, gap detection |
| AF-REQ-003, AF-REQ-004 | T02 | registered tools + denied permissions |
| AF-REQ-005, AF-REQ-006 | T03 | minimal tools, immutable AgentSpec |
| AF-REQ-007 | T04 | sandbox and spend bounds |
| AF-REQ-008, AF-REQ-009 | T05 | independent rubric and hard safety gates |
| AF-REQ-010, AF-REQ-011 | T06 | bounded repair + GEPARD regression |
| AF-REQ-012 | T07 | injected crash/resume no duplicate effects |
| AF-REQ-013 | T08 | independent A2A client invocation |
| AF-REQ-014, AF-REQ-015 | T09 | approvals, release, rollback |
| AF-REQ-016 | T10 | two different tasks, zero core code changes |
| AF-REQ-017 | T11 | optional Soup/LoRA benchmark + data rights |
| AF-REQ-018 | T12 | optional Pi Durable adapter benchmark |
| AF-REQ-019 | T13 | redacted trace, tenant isolation |
| AF-REQ-020 | T14 | adversarial security scenarios |
| AF-REQ-021 | T15 | SDD and CI enforcement |
| AF-REQ-022 | T16 | legal data scope and escalation |
| AF-REQ-023 | T17 | LiteLLM gateway: tenant/provider isolation, budgets, failure-handling |
| AF-REQ-024, AF-REQ-025 | T18 | typed business package, attachment manifests, rights, tenant access |
| AF-REQ-026, AF-REQ-027 | T19 | secure document ingestion, traceable extracted rules, generated output templates |
| AF-REQ-028 | T20 | independent holdout access isolation and contamination tests |
| AF-REQ-029 | T21 | minimal tool mapping, explained selection, missing capability blockers |
| AF-REQ-030 | T22 | readiness, immutable task revision, change-triggered regression |

| AF-REQ-038..040 | T30..T32 | two independent builds, durable harness and safe optimization surfaces |
| AF-REQ-041..044 | T33..T36 | GEPARD, ReAct, memory verification and A2A attribution |
| AF-REQ-045..047 | T37..T39 | AgentStore versions, Orchestrator-led improvement and twin E2E |
| AF-REQ-048 | T40 | LiteLLM cheaper model non-inferiority and total cost-per-correct-operation |

Fill exact CI/evaluation evidence in implementation PR. Do not invent links.
