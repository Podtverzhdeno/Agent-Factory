# Spec Kit-inspired review checklist

Change:
Reviewer:
- [ ] Business outcome is measurable and external to the agent's claims.
- [ ] Minimum capability tools and explicit permissions defined.
- [ ] OpenSpec requirements contain positive and negative scenarios.
- [ ] Requirements → design → tasks → tests → evidence traceability.
- [ ] Threat model: prompt injection, MCP, malicious tools, SSRF, tenant isolation.
- [ ] Fault/retry/idempotency and rollback strategy reviewed.
- [ ] GEPARD changes have baseline and independent holdout.
- [ ] Code/static and domain/E2E tests actually executed; missing ones marked pending.
- [ ] Human approvals and client data rights confirmed.

Verdict: PASS / CHANGES REQUIRED / BLOCKED.
