# I00 C0 preparation · 2026-10-28

C0 is **not yet READY**. This branch adds a fail-closed Next.js shell and typed interface stubs without entering A01–A10 directories. A03 Issue #10 comment 6466890498 was verified: RFQ and certificate design complete as preparation, no A03 claim/code.

- [x] Isolated `integration/studio-c0-prep-20261028` source branch with proposed Next/React/TypeScript/SCSS root.
- [x] Workspace/Operator shell protected fail-closed; 15 operator section names and placeholder ports available.
- [ ] Reproducible package installation, pnpm/npm policy and lockfile; typecheck/lint/build real run on pinned SHA.
- [ ] Review dependency/Next security and current transitive lockfile.
- [ ] Freeze BASE_SHA, source OpenAPI, BFF read/command contract and routes with A01 / service owners.
- [ ] Ratify ADR-0002 before any topology-dependent implementation.
- [ ] Wire actual session/workspace/tenant permissions via A01; publish actual UI from A02.
- [ ] Implement serialized task claim coordinator Issue #18, generate fencing tokens, and execute LEASE-001..016.
- [ ] Actual Task Intake / file ingestion and grants remain unimplemented. A03 stays BACKLOG until authorized lease.

**A03 request acceptance:** typed draft/revision/409, upload receipt+provenance, Registry selection≠grant, owner-approved immutable READY, separate idempotent Build receipt; see Issue #10 for exact semantics.
