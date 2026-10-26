# Tasks — twin-agent-harness

Status: all implementation tasks are OPEN; do not mark complete without executable evidence.

- [ ] T30 (AF-REQ-038) Implement independent BTP_A/B snapshots and explicit Orchestrator scheduling of two Builder jobs; verify tenant isolation, partial failure and replay.
- [ ] T31 (AF-REQ-039) Compile LangGraph checkpointing, short-term memory and separate long-term memory from initial harness; verify multi-turn and crash/recovery including external idempotency.
- [ ] T32 (AF-REQ-040) Specify immutable, typed and permission-scoped harness optimization surfaces; verify no prompt optimization can change tool auth, safety gates or evaluation gold.
- [ ] T33 (AF-REQ-041) Improve supported prompts and tool/argument descriptions via GEPARD and bounded alternative tool/MCP selection via Registry; verify actual tool schemas and permissions remain valid.
- [ ] T34 (AF-REQ-042) Capture observable ReAct plan/action/observation events and graph transitions; test stop criteria, false completion, missing tool effects and loops without requiring private hidden reasoning.
- [ ] T35 (AF-REQ-043) Evaluate short-term and long-term memory separately: TTL, provenance, stale facts, summarization, deletion and cross-tenant boundaries.
- [ ] T36 (AF-REQ-044) Attribute joint A2A defects to A/B and validate independent/frozen-partner cross-play, adverse cases and private gates.
- [ ] T37 (AF-REQ-045) Build versioned tenant-scoped AgentStore candidates/releases, manifests, A2A Agent Cards, compatibility evidence and rollback; verify independent approvals.
- [ ] T38 (AF-REQ-046) Implement Orchestrator repair policy and direct conditional Soup trigger after permitted diagnosis; retest independently and bound time/cost/attempts.
- [ ] T39 (AF-REQ-047) Execute full bilateral end-to-end synthetic pilot from two BTPs through independent builds, A2A tests, one targeted repair and gated AgentStore release.
- [ ] T40 (AF-REQ-048) Implement Model Cost–Quality Benchmark with LiteLLM candidate eligibility, frozen model baseline, per-node/tenant A/B comparisons, independent holdout non-inferiority, full cost-per-correct-task and safe rollback; test capability mismatch, insufficient evidence, cheap-but-low-quality, and shared A2A regression.

Evidence must include exact AgentSpec hashes, model/provider configuration and price snapshot, task/trace IDs, both tenants' policy versions, datasets, code revisions, CI output, cost/quality uncertainty and release approvals. All checks remain pending until executed.
