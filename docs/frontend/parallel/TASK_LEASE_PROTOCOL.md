# Task coordination: visible claims, UTC activity trail, 2-hour stale detection and safe takeover

**Status:** PROPOSED coordination protocol; **not yet a running distributed scheduler or enforceable CI claim lock.** Date: 2026-10-28.
**Scope:** Studio A01–A10 and I00, extensible to backend workstreams. The ten Axx task packets keep exclusive folder ownership; one agent can assume a **task lease** only if the target task's file ownership is compatible. A task lease NEVER overrides module/file ownership.
**Canonical requirements:** openspec/changes/studio-cjm-parallel/specs/studio-cjm/spec.md (AF-REQ-126..131 proposed). **Do not** use issue/PR update timestamps alone as the progress clock.

## 1. Source of truth and surfaces

- **One GitHub Issue per independently assignable task** (STU-T03..STU-T12 for first ten frontend packets). A task Issue is the **current coordination read model**, not a copy of an OpenSpec task. Its structured metadata contains identity, live state, lease and references.
- **One append-only Issue comment per event** (CLAIM, HEARTBEAT, PROGRESS, BLOCKED, RELEASE, STALE_DETECTED, TAKEOVER_REQUESTED, TAKEOVER_GRANTED, HANDOFF, DONE, VERIFIED, ABANDONED). The GitHub author and created_at are independently recorded by GitHub; agent ID alone is not proof of identity.
- **OpenSpec requirement/tasks are the durable product requirement and human/auditable implementation checklist**; record eventual verified result and handoff there by integrator, but never have multiple workers rewrite the same central tasks.md for each heartbeat. OpenSpec task remains unchecked until tests/executable evidence pass.
- **PR and branch** are actual code-progress evidence: description must include \`Task: STU-Txx\`, \`Studio-Agent: Axx\`, \`Claim-Generation: n\`, \`Base-SHA: <sha>\`, and \`Closes #issue\` only after verified acceptance. Draft PR must not falsely claim completion.
- **Global dashboard** is generated from GitHub Issues and their last accepted events; no manually maintained single JSON status file with 10 concurrent writers. A board may show current owner/status/time as an **as-of stamped projection**. Recompute from Issue on any claim/takeover, do not trust cached list.

## 2. Statuses and two independent clocks

### State transitions

\`\`\`text
BACKLOG -> AVAILABLE -> CLAIMED -> IN_PROGRESS -> IN_REVIEW -> VERIFIED -> DONE
                |          |             |             |
                |          +-> BLOCKED ---+             +-> CHANGES_REQUESTED -> IN_PROGRESS
                |          +-> PAUSED / RELEASED -> AVAILABLE
                +-> STALE_CANDIDATE -> TAKEOVER_PENDING -> REASSIGNED -> IN_PROGRESS
                +-> CANCELLED (only I00)
\`\`\`

- \`BACKLOG\`: prerequisites not satisfied, do not claim.
- \`AVAILABLE\`: C0/contract dependencies and paths ready; claimable with coordinator-granted lease.
- \`CLAIMED\`: exclusive lease granted but work not yet started; start/progress expected within 20 minutes.
- \`IN_PROGRESS\`: legitimate owner working, lease currently held; **no automatic assumption of healthy progress**.
- \`BLOCKED\`: source dependency or external review prevents progress; must report blocker and \`required_action\`; still tracked but **not automatically reassigned** unless an authorized, independently executable part exists.
- \`IN_REVIEW\`: PR linked and tests submitted; not stale merely because code unchanged for two hours while human review proceeds; track reviewer/CI wait separately.
- \`STALE_CANDIDATE\`: >=120 minutes since last **meaningful progress** while status IN_PROGRESS (or CLAIMED with no progress), not equivalent to abandoned work.
- \`TAKEOVER_PENDING\`: independent coordinator verifying branch, PR, merge and current owner acknowledgment.
- \`REASSIGNED\`: claim generation incremented and prior lease revoked; only then new agent may edit relevant files.
- \`VERIFIED\`: integrator confirmed relevant acceptance tests on integration SHA.
- \`DONE\`: integrator closed issue and approved evidence. A green SDD/doc CI alone is insufficient.

### Clocks (UTC timestamps, RFC3339 +02 etc browser rendering only)

- \`claimed_at\`: claim success timestamp (not request).
- \`last_heartbeat_at\`: owner is reachable. Update **at least every 20 min while active**; heartbeat is NOT meaningful progress.
- \`last_progress_at\`: timestamp of most recent accepted **substantive** update with artifact evidence (commit SHA, PR diff/new test run/build issue outcome, approved spec/fixture with hash, confirmed blocker resolution). Repeated empty "working" messages do NOT change it.
- \`status_changed_at\`: when logical state last transitioned, distinct from progress; not used alone for stale detection.
- \`lease_expires_at\`: now + 30 min from heartbeat, **used to flag possible absence**, not enough for takeover.
- \`stale_check_at\`: last_progress_at + 120 min if IN_PROGRESS. A valid exception (CI running, rate limits, explicit expected long test/human review) may be set by I00 with an expiry and evidence.
- \`updated_at\`: UI projection refresh, may be newer than all clocks; do not infer progress from it.

**2-hour rule (user instruction):** if status remains \`IN_PROGRESS\` and last meaningful progress unchanged for > 120 min, mark STALE_CANDIDATE. Immediately look for FREE/AVAILABLE compatible task FIRST. Only when **no compatible unclaimed available task** exists should agent request stale takeover. Thus any heartbeat within the 2h does not hide stagnation. If a long-running test has real job URL/updated logs, mark legitimate active investigation with bounded grace through I00.

**No fabricated timestamp:** \`claimed_at\` and \`last_progress_at\` stay \`null\` on not-yet-started issues. GitHub \`created_at\` is not a claim.

## 3. Task record schema

Illustrative Issue body metadata managed **only by coordinator**, not mutable by arbitrary workers:

\`\`\`json
{
  "schema_version": "studio.tasklease.v1",
  "task_id": "STU-T05",
  "packet": "docs/frontend/parallel/A03_task-intake.md",
  "source_requirement_refs": ["AF-REQ-101", "AF-REQ-102"],
  "status": "BACKLOG",
  "priority": 5,
  "allowed_owner_roles": ["A03"],
  "current_owner": null,
  "lease_generation": 0,
  "claimed_at": null,
  "status_changed_at": null,
  "last_heartbeat_at": null,
  "last_progress_at": null,
  "lease_expires_at": null,
  "current_branch": null,
  "base_sha": null,
  "linked_prs": [],
  "last_evidence_sha": null,
  "blocked_reason": "WAITING_FOR_C0",
  "required_action": "INTEGRATOR_FREEZE_C0"
}
\`\`\`

This metadata is design schema, not real live issue state until issue creation and coordinator are provisioned. Exact issue structured block format should use \`<!-- studio-tasklease-v1 ... -->\` enclosing strict JSON for deterministic read. No raw secrets/customer data in issue body or comments. Task record \`lease_generation\` is a **fencing token**: old owner or code from generation n cannot modify/finalize a task once generation n+1 is granted.

Recommended event comment:

\`\`\`text
[STUDIO-TASK-EVENT v1]
event: PROGRESS
task_id: STU-T05
actor_id: A03
lease_generation: 1
occurred_at_utc: 2026-10-28T10:25:00Z   # server-issued, not browser clock
status_after: IN_PROGRESS
summary: "Add BTP draft validation, tested 409 revision conflict"
evidence: commit:<sha> / pr:#<n> / CI:<run-id>
next_action: "Implement file upload rejected/retry states"
blocker: none
[/STUDIO-TASK-EVENT]
\`\`\`

Event comments are append-only: if corrections needed, add SUPERSEDES(event_id) event, do not rewrite GitHub history. Server GitHub comment ID and created_at are the audit anchor, not the agent's free-form timestamp. PR code remains in owned branch and never moves into another's branch by takeover.

## 4. Agent behavior algorithm

\`\`\`text
EVERY START / RESUME:
  1. Sync task issue index from GitHub (not a local static JSON).
  2. If already owner, verify lease_generation, state, branch and last event.
  3. If no active owned task: choose eligible AVAILABLE task
     whose prerequisites and file ownership are compatible.
  4. Request CLAIM via serialized coordinator; never start writing
     until coordinator confirms lease + generation + timestamp.
  5. Write claim event, branch/PR reference, mark IN_PROGRESS.
  6. Send heartbeat at least every 20 min and real progress update on
     meaningful advancement (recommended at least every 30 min if advancing).
  7. If >120m no progress, issue becomes STALE_CANDIDATE,
     not automatically owned by another agent.

WHEN SEEKING NEXT TASK:
  1. Prefer eligible AVAILABLE tasks, ordered priority/dependencies.
  2. If none, query STALE_CANDIDATE tasks, including GitHub issues,
     all open/closed/draft PRs, base/head SHAs, latest commits, current
     CI runs, comments and merge status across the repo.
  3. If PR merged or work present and verified, mark IN_REVIEW/VERIFIED;
     DO NOT take over. If PR has meaningful new commits/tests after last
     progress, request source state reconciliation and notify owner.
  4. If work truly stalled and no compatible free tasks, request
     TAKEOVER_PENDING with evidence, changed-file ownership plan,
     explicit reason and current owner notice.
  5. I00/coordinator re-reads task + PR at commit/issue revision,
     verifies stale evidence, no new progress, owner grace/ack criteria,
     and grants only one REASSIGNED lease with generation +1.
  6. New owner reads spec, branch, PR, test logs, code and uncommitted-
     work risk; creates NEW branch from integrated base, selectively
     cherry-picks safe commits with attribution if needed, never pushes
     to predecessor branch and never edits unowned paths.
  7. New owner appends precise HANDOFF/TAKEOVER events and spec note:
     "Работа агента Axx приостановлена: последняя подтверждённая
     активность YYYY-MM-DDTHH:MM:SSZ, статус IN_PROGRESS, нет
     свободных совместимых задач, GitHub PR #N/commits проверены,
     невыполненные пункты ..., задачу принял Ayy в ..., поколение
     владения n → n+1." Only after coordinator GRANTED.
  8. Old owner's subsequent attempts using generation n must be refused.
\`\`\`

**Critical exception:** if original owner's PR contains unmerged but useful code, do NOT describe it as "nothing done". Report exact completed vs unfinished files/tests; propose taking residual task separately. 2 hours is a **review threshold**, not evidence of abandonment.

## 5. Atomicity and enforcement

**GitHub Issue assignee, label or comment ALONE are not a distributed lock.** Two agents could race to update the same Issue or both read AVAILABLE. Use **single-writer coordinator**:

- Recommended small-project implementation: GitHub Actions job accepting only authenticated \`claim/progress/heartbeat/release/takeover\` requests; all state-changing operations serialized by one repository-wide \`concurrency\` group with **\`queue: max\` and \`cancel-in-progress: false\`**. State change rereads Issue immediately inside the serialized job, applies authorization + ownership allowlist + generation check, writes issue metadata and appends audit comment. Do not execute arbitrary code supplied in comments. Protect against unauthorized issue commenters; use GitHub permission API and allowlisted agent service identities.
- Alternative when Actions delays/retries matter: a tiny trusted dispatcher API with transactional row update \`WHERE task_id=? AND generation=? AND status=?\` (CAS) and immutable events. Do not create a service solely for this if Actions meets reliability.
- Actions may delay or be disabled; actual state must be read before writing code. If coordinator is unavailable: **NO NEW CLAIM/TAKEOVER**, work on already owned branch can continue conservatively but PR cannot be merged as accepted until lease verified.
- Protect branch/code paths via CI diff ownership checker comparing all changed paths to task's exclusive glob. The A01–A10 packet \`WORK_OWNERSHIP_MANIFEST.json\` is a guardrail. A worker who takes an existing A03 task must be explicitly granted **A03 path rights for that task generation** by coordinator; if their other active task is in another module, they must pause it first.
- Every task state update carries \`lease_generation\` and claim ID; takeover increments generation. Workflow CI rejects changes or completion attempted with revoked generation, including PR edited after revocation.
- **Important:** GitHub Actions \`concurrency\` serializes running jobs but queued order is not a strict FIFO task queue. The default pending queue can replace/cancel older pending jobs; **\`queue: max\`** is required so that simultaneous claims are not silently discarded (up to 100 pending; still revalidate Issue immediately inside the lock). This is supported in GitHub Actions since May 2026 ([GitHub docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)). Server-side claim validation determines the sole winner; users see REQUESTED vs GRANTED clearly.
- Existing docs/frontend/parallel/WORK_OWNERSHIP_MANIFEST.json is a static design allowlist, not a dynamic lock. The task Issue and trusted dispatcher add live mutual exclusion; neither can overwrite owner-approved architectural constraints.

## 6. Required takeover evidence checks

Before \`TAKEOVER_GRANTED\`, capture in the Issue comment and coordinator audit:

1. Issue task ID/status/owner/lease generation, last meaningful progress UTC, heartbeat UTC and elapsed minutes >=120.
2. Link to original owner's active Draft/open/closed/merged PR(s), full current branch head SHA, commits since last progress and CI running/completed results; search **by task ID** + owning branch, not PR title alone.
3. Whether code/tests exist but not merged; identify exact partial work to preserve and blockers. Rejected CI is not zero work.
4. Confirm there are **zero compatible AVAILABLE tasks** after evaluating dependencies and actual file ownership; snapshot their IDs.
5. Confirm current owner has been notified and no new meaningful evidence appeared during bounded coordinator verification. Proposed default grace 10 minutes; automated rerun after grace, with human approval for critical/release/security tasks.
6. Ensure old owner is marked PAUSED/REASSIGNED and old generation invalidated **before** granting new generation. New branch and authorization scoped to owned paths.
7. Record signed/attributed GitHub claim time and new owner, reason, original PR links and resumed plan in Issue + feature-local \`HANDOFF.md\` (if path permitted). Integrator updates OpenSpec \`tasks.md\` with takeover note when incorporated, not every heartbeat.

Human approval **always required** for task takeover involving release gates, incident response, secret/IAM policy or owner ADR decisions; never auto-transplant live credentials or incomplete production operations.

## 7. UI board design

Columns: **Backlog / Available / In Progress / Needs Review / Blocked / Stale Candidate / Takeover Pending / Done**. Each task card shows:
- Task ID and short title, owning feature/module, work packet and priority.
- Current assigned Axx, GitHub actor identity, claim UTC and timezone-local display.
- Current status, status_changed_at, last_heartbeat_at, last_progress_at, **age of last meaningful progress** in minutes, lease generation and lease expiry.
- Base/head SHA, last meaningful commit, PR number/state, CI state, blocker, next action.
- Allowed actions Claim / Log Progress / Release / Request Takeover shown only to authorized actors (server rechecks).
- Stale reason and override approval shown where relevant; no false "agent stopped" based solely on elapsed time.
- Source-as-of and refresh; Issue links open original immutable comment stream.

Example: **STU-T05 — BTP Wizard** / A03 / IN_PROGRESS / claimed 2026-10-28 10:00 UTC / last progress 10:42 / heartbeat 11:02 / no takeover because free A04 task exists. These timestamps are **example values only**; real issues use server timestamps.

## 8. Acceptance tests for coordination service (not executed yet)

| ID | Scenario | Must verify |
| --- | --- | --- |
| LEASE-001 | Two agents request same AVAILABLE issue concurrently | Exactly one granted claim; second sees already owned and a winner reference |
| LEASE-002 | Heartbeat 20 min updates lease but no meaningful progress for >120 min | STALE_CANDIDATE based on last_progress, not heartbeat |
| LEASE-003 | Task stale but another compatible AVAILABLE exists | Worker takes free task; stale task not auto-stolen |
| LEASE-004 | No free tasks, stale task has new PR commit or running CI | Reconcile to active/review; takeover withheld |
| LEASE-005 | No free task, no progress, PR incomplete and owner offline | Coordinator waits grace, grants new generation once and records exact links |
| LEASE-006 | Old generation tries to progress after takeover | Denied, not overwriting current owner |
| LEASE-007 | Old PR already merged / issue done | No takeover, mark verified after tests |
| LEASE-008 | Same task status/claim writes race across two dispatcher runs | Serialized CAS/validation yields one owner |
| LEASE-009 | Agent tries to take module with unauthorized path | Denied until integrator explicitly grants task-scoped path rights |
| LEASE-010 | GitHub/API/Actions unavailable | No new claim; no silent false state, retry safely |
| LEASE-011 | Long-running test with actual CI run URL and bounded grace | No false abandonment, explicit defer/review |
| LEASE-012 | Owner releases task voluntarily | Event/status and branch/PR handoff preserved; task AVAILABLE only after integrator verifies safe handoff |
| LEASE-013 | Original owner resumes from stale old branch | Cannot push into another's active branch/claim completed work using revoked generation |
| LEASE-014 | Critical security/release task takeover | Human reviewer approves before changed ownership |
| LEASE-015 | Agent sends fake heartbeat with no code/PR proof | Clock can move for liveness, meaningful progress clock unchanged |
| LEASE-016 | Timestamp spoof in comment | Actual GitHub actor/created_at/coordinator time wins over free-text timestamp |

## 9. Integrator/agent checklist

- [ ] I00 creates GitHub Issues and initializes task metadata with null claim/progress dates (until C0 exists, status BACKLOG).
- [ ] I00 defines approved task claimant identities and assigned work packet/path rights, deploys the serialized claim coordinator.
- [ ] I00 runs LEASE-001..016 and verifies an actual two-agent race under the deployed workflow.
- [ ] CI enforces ownership and generation on every code PR, incl. takeover.
- [ ] Every agent reads Issue and confirms current lease before starting a task; sends liveness+evidence; no bypass through comments.
- [ ] Every agent pauses owned work before picking a second task if file scopes could overlap.
- [ ] Every eligible stale takeover records Issue/PR/commits/CI evidence and safe handoff with exact UTC timestamps.
- [ ] I00 updates canonical OpenSpec only after accepted handoff/evidence and keeps verified work separate from in-progress.

**This document is a strict implementation specification and operating policy. Until dispatcher/CI has been deployed and verified, mutual exclusion is not technically enforced; agent prompts alone are advisory.**