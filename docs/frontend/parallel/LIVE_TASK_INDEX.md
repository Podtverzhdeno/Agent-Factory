# Live GitHub task tracking index (bootstrap)

**Status snapshot only: 2026-10-28.** GitHub Issue records are the live task-state source, not this index table. Every issue starts BACKLOG/WAITING_FOR_C0 with owner=null and null claim/progress time; no coding agent has actually claimed these tasks yet.

**Read live:** [All Studio task Issues](https://github.com/Podtverzhdeno/Agent-Factory/issues?q=is%3Aissue+is%3Aopen+%5BStudio%5D) · [Task lease / takeover rules](TASK_LEASE_PROTOCOL.md).

| Task | Workstream | GitHub live task | Initial (not live) snapshot |
| --- | --- | --- | --- |
| STU-T03 | A01 · Платформа, BFF, IAM | [Issue #8](https://github.com/Podtverzhdeno/Agent-Factory/issues/8) | BACKLOG, owner unknown, blocked C0 |
| STU-T04 | A02 · Дизайн-система и графики | [Issue #9](https://github.com/Podtverzhdeno/Agent-Factory/issues/9) | BACKLOG, owner unknown, blocked C0 |
| STU-T05 | A03 · Мастер BTP | [Issue #10](https://github.com/Podtverzhdeno/Agent-Factory/issues/10) | BACKLOG, owner unknown, blocked C0 |
| STU-T06 | A04 · Каталог агентов и workflow | [Issue #11](https://github.com/Podtverzhdeno/Agent-Factory/issues/11) | BACKLOG, owner unknown, blocked C0 |
| STU-T07 | A05 · Runtime и запуски | [Issue #12](https://github.com/Podtverzhdeno/Agent-Factory/issues/12) | BACKLOG, owner unknown, blocked C0 |
| STU-T08 | A06 · Evaluation, GEPARD, релизы | [Issue #13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13) | BACKLOG, owner unknown, blocked C0 |
| STU-T09 | A07 · Ops 1–5 | [Issue #14](https://github.com/Podtverzhdeno/Agent-Factory/issues/14) | BACKLOG, owner unknown, blocked C0 |
| STU-T10 | A08 · Ops 6–10 | [Issue #15](https://github.com/Podtverzhdeno/Agent-Factory/issues/15) | BACKLOG, owner unknown, blocked C0 |
| STU-T11 | A09 · Ops 11–15 | [Issue #16](https://github.com/Podtverzhdeno/Agent-Factory/issues/16) | BACKLOG, owner unknown, blocked C0 |
| STU-T12 | A10 · Совместный A2A-конструктор | [Issue #17](https://github.com/Podtverzhdeno/Agent-Factory/issues/17) | BACKLOG, owner unknown, blocked C0 |

**Important:** the Axx code module owner and a live task lease are different. “Agent A03” in this table is an **intended workstream/packet**, not evidence that an agent has started or received a grant. Any takeover must be granted by the serialized coordinator with a new generation and a scoped path delegation.

## Every new agent must follow this sequence

1. Open GitHub live Issues; read timestamps, last progress, PR and leases. Do not rely on this static table.
2. Select compatible AVAILABLE task; request atomic claim and wait for GRANTED.
3. Log claim (UTC, actor, task, generation, branch), send heartbeat every <=20min and substantive progress with SHA/PR/test link when there is work. A heartbeat alone does not reset last meaningful progress.
4. After >120min without substantive progress, flag stale; if any compatible free task exists, take free work first.
5. Only if none free: inspect issue, branch, Draft/open/merged PRs, commits, CI and last actor events, request TAKEOVER_PENDING with reason and evidence. No automatic overwrite based on status age alone.
6. After coordinator grants generation+1, log exact old/new owner, times, original PR and remaining scope in Issue; integrator updates canonical OpenSpec handoff note. New agent starts a new branch; old generation forbidden.

Until the claim coordinator and CI generation check are deployed, these issues are **bootstrapped tracking surfaces**, not an enforceable real-time assignment service. See STU-T19–23 in [OpenSpec tasks](../../../openspec/changes/studio-cjm-parallel/tasks.md).