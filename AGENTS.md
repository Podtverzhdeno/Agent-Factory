# Agent Factory — mandatory instructions for coding agents

Read in order: README.md → .specify/memory/constitution.md → docs/process/SDD.md → current openspec/changes/*/proposal.md, design.md, tasks.md and delta specs → docs/quality/gates.md.

## Workflow

1. Investigate repository state. This is a greenfield project: do not assume functionality exists.
2. Create/update one OpenSpec change before behavioral code: proposal, requirements with GIVEN/WHEN/THEN or WHEN/THEN scenarios, architecture decisions, tasks.
3. Map each requirement ID to a task, executable test and evidence. Clarify assumptions, attack the design for failure modes and update design as needed.
4. Implement smallest vertical slice behind typed interfaces. Make no claims of success until tests, evidence and security checks have been executed.
5. Put experiments in an isolated sandbox. No autonomous agent/tool is allowed to read developer secrets, change production permissions, transfer confidential customer datasets between tenants, make payments or issue live orders.
6. Never silently weaken evaluator thresholds, delete negative tests or promote an agent only because its own LLM claims to have succeeded.
7. Every generated Agent Spec and tool binding is validated; deny by default, explicit capability grants, credentials injected at runtime, audited effects.
8. Keep the A2A transport boundary separate from business logic. MCP is a tool protocol, not an authorization mechanism.
9. Do not equate Pi Durable with exactly-once effects; use idempotency keys, outbox/inbox patterns and external state reconciliation. Durable implementation is swappable.
10. Optimization: establish immutable baseline + training/validation/hidden holdout. GEPARD changes prompt/harness in sandbox, never trust test-set-only improvements. Soup training only after justified data and economics review.
11. Document dependency licenses, threat model, data retention and rollout/rollback for each new external service.
12. Submit a PR, do not directly merge to main. Checkboxes in tasks.md only after verifiable result. When blocked, leave task open and report blocker.

## Quality gates

Requirement → design/ADR → task → test → captured evidence. Scripts are useful checks, not replacements for domain tests, security review or customer acceptance. See docs/quality/gates.md.

## Language

Requirements and code contracts: precise English. Product explanations, customer communications: Russian where appropriate. All executable protocols use explicit schemas, not natural-language conventions alone.
