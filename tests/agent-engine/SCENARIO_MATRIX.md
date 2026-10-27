# Agent Factory — versioned business scenario gap matrix

**Scope:** Workstream 04: Builder, Runtime, MCP/tools, LiteLLM and A2A boundary.
**Updated:** 2026-10-27. Scenarios derive from existing OpenSpec
`bootstrap-factory-mvp`, `a2a-bilateral-evaluation`, and
`twin-agent-harness`; this file introduces **no new owner-ratified architecture**.

Statuses: **COMPONENT** = a local mock-backed unit/contract test exists (current revision's pass not implied);
**CANDIDATE** = test/config exists but that execution is not verified;
**GAP** = no implementation / no independent proof. An A2A task reaching
`COMPLETED` is **never** a business outcome acceptance oracle.

| ID | Business scenario / pass condition | Requirement | Current proof | Gate / next action |
|---|---|---|---|---|
| B01 | Buyer supplies XLSX RFQ; catalog lookup produces correct draft (2 × $12 = $24) | 024–027, 029 | COMPONENT `test_synthetic_demo.py` | Real multi-sheet, units, provenance, macro safety absent |
| B02 | Read-only approved supplier search yields evidence-backed response | 005, 007, 016 | COMPONENT `test_synthetic_demo.py` | Real connector authentication + source freshness |
| B03 | Buyer A and supplier B approve independently; distinct AgentSpecs and scopes | 031, 038, 040 | COMPONENT + real SDK wire smoke `test_bilateral_official_a2a.py` | Independent approvals, orchestrator dispatch and real two-tenant storage still OPEN |
| B04 | Both parties exchange incomplete RFQ, clarification, quote Artifact, acceptance | 032, 037, 047 | COMPONENT deterministic dialogue oracle (not A2A transport) | Two independent official A2A SDK endpoints and protocol client/server |
| B05 | Required SKU/quantity absent; ask for missing data, do not invent them | 024, 032 | COMPONENT mock clarification sequence and forgery denial | Runtime-backed question/answer lifecycle and user-confirmed continuation |
| B06 | Supplier returns quotation with wrong currency, units or totals | 008, 037, 044 | COMPONENT `test_bilateral_quote_oracle.py` (18 local cases, exact Decimal) | Bind oracle to verified ArtifactStore and signed trace; real A2A run |
| B07 | Unknown/unapproved catalog MCP tool is suggested | 003–005, 029 | COMPONENT deny coverage | Real Registry signatures, MCP integration and audit |
| B08 | One party requests another tenant's prompt, artifact or memory | 004, 031, 036, 043 | COMPONENT tenant denial | Shared artifact store permissions and trace redaction E2E |
| B09 | User attempts live purchase/payment with only read/draft grants | 004, 009, 040 | COMPONENT denies | Human-approved consequential effect workflow in another milestone |
| B10 | Worker dies after creating a draft; restart must not duplicate effect | 012, 032, 039 | COMPONENT SQLite process-kill + guarded PG CANDIDATE | Real Postgres recovery, external reconciliation and outbox |
| B11 | Partner timeout/disconnect mid-dialogue; preserve A2A task state | 032, 039 | GAP | Official A2A SDK + real PG checkpoint test; fault injection |
| B12 | One side's Build fails; other side's approved artifact remains intact | 029, 038 | CANDIDATE `test_bilateral_business_scenarios.py` | AgentStore cross-service orchestration |
| B13 | Supplier file contains prompt injection, macros or malicious attachment | 007, 025–028 | COMPONENT tool deny, no file-ingest proof | Dedicated MIME parser sandbox / provenance oracle |
| B14 | Proprietary partner data enters other tenant's optimization trace | 031, 034, 036 | GAP | Consent-aware artifact filtering and independent redaction |
| B15 | GEPARD improves fluency but harms tool calls or private-data policy | 009, 011, 035, 041 | GAP | Independent eval, sealed holdout and baseline rollback |
| B16 | A1/B1 succeeds but A1/B0 fails against a frozen counterpart | 035, 044, 047 | GAP | Paired cross-play acceptance (A0/B0, A1/B0, A0/B1, A1/B1) |
| B17 | Cheaper model drops required tool invocation or lacks JSON support | 023, 048 | COMPONENT format checks; no business A/B proof | LiteLLM real proxy, per-model heldout non-inferiority |
| B18 | Released AgentSpec revoked while A2A requests are in flight | 013, 045 | COMPONENT dynamic revocation tests | Signed AgentStore release lookup and task lifecycle policy |
| B19 | Business owner revises SOP/template; agent must get new revision | 027, 030, 045 | COMPONENT AgentSpec digest/version | Upstream artifact event + downstream re-evaluation |
| B20 | Correct A2A completion without verified quote Artifact | 008, 037, 042 | COMPONENT test asserts FAILED without quote | Real cross-service Artifact and effects oracle remains OPEN |
| B21 | Model/router exceeds real budget under concurrent tenants | 007, 023, 048 | COMPONENT estimated-cost stop; real quota GAP | Database-backed LiteLLM hard spending limits |
| B22 | Sealed evaluation output or near-duplicate leaks into optimization | 028, 035 | GAP | Independent holdout isolation and contamination checks |

## First vertical pilot: buyer → supplier RFQ

1. **Independent intake:** organization A (buyer) uploads signed task package:
   XLSX, expected quantity/unit and authorized catalog scopes; organization B
   (supplier) uploads its independent price-list/rules and privacy policy.
2. **Assembly:** create AgentSpec A0 and B0 from the *same* Builder implementation
   with separate tenant/grants; deny any missing connector.
3. **Dialogue:** buyer sends versioned `Message` with authorized attachment Part,
   supplier requests clarification if a unit is missing, then emits a versioned
   quote business Artifact via an A2A `Task`. This has **not** been implemented
   end to end.
4. **Independent oracles:** buyer verifies SKU, quantity, currency, total,
   source references and allowed disclosures; supplier verifies allowed price,
   margins, scope, no private data loss. Joint result requires both PASS.
5. **Failures:** inject supplier disconnect after draft, duplicate message,
   wrong currency, forged Agent Card, revoked principal, expired catalog
   prices, prompt injection in an XLSX cell, and denied payment tool.
6. **Release:** *only* independent acceptance + owner authorization allows
   separate A0/B0 release. No automated promotion in this workstream.

## Suggested priority after the component-only baseline

**P0:** B03/B04/B06/B08/B09/B10/B11/B20 (valid independent bilateral
outcome, tenant safety and crash recovery); **P1:** B05/B07/B12/B14/B18/B19;
**P2:** B13/B15/B16/B17/B21/B22. All P0 cases must run against actual
PostgreSQL, registered MCP and official A2A SDK before claiming E2E PASS.

## Test evidence discipline

`test_bilateral_business_scenarios.py` deliberately simulates two
organizations via separate Builder/Runtime ports. **It is not a true A2A
protocol run.** The existing official SDK and Postgres tests remain optional
and have not passed on the deployment branch. Never count a mocked case as
independent business or production acceptance.

**Platform state (latest read):** Railway `adequate-respect` now has a live PostgreSQL
service and live `Agent-Factory` from workstream 01. `agent04-integration-gate`
is deploying an older test revision and has not passed the strict gate. Do not
infer that a running database or unrelated service is Agent 04 acceptance.
Coordinate any deployments or cross-workstream configuration changes.

## Important infrastructure evidence

At SHA `0cd81ba`, Railway built the integration container but failed
`compileall` because `agent_builder/core.py` contained a repeated and
unterminated field definition at line 62. The issue is fixed on a newer
branch commit `569a61f` but **no successful rebuild on that commit was
observed**. A subsequent test deployment targets `a1abf341` and emits Ruff failures;
the latest scenario-oracle tests ran independently on a local synthetic fixture,
**18 passed**. The complete Agent 04 suite and real official-SDK E2E remain
unverified on the newest GitHub SHA.

### B2B business oracle component evidence (2026-10-27)

`test_bilateral_quote_oracle.py` uses immutable RFQ / Quote / Event records,
exact `Decimal` prices and separate hard policy limits for the buyer and
supplier. It denies forged clarification, duplicate offers, cross-tenant
quote ownership, stale/missing catalog provenance, private-field disclosures,
wrong units/currency/totals, missing quote and tampered artifact hash. It
**never** trusts the generated success message. A standalone local invocation
of this exact fixture reported **18 passed**.

Important limits: SHA-256 checks structural integrity only, not signature,
issuer authenticity or provenance verification against a trusted ArtifactStore.
Events in this fixture are authored data, not intercepted official A2A SDK
messages. Real tenant authorization, privacy-consent enforcement and the
independent buyer/supplier release gates are still integration blockers.

## Current executable integration evidence (supersedes older notes)

Railway revision `b6d7c526` ran the real optional dependencies on
2026-10-27. Compile succeeded, Ruff **0**, Pyright **0**, pytest
**144 passed, 2 skipped**. The official A2A SDK smoke now includes
independent buyer and supplier servers with separate clients, specs,
principal scopes and bearer-token denial across company boundaries.
This is **a real transport test**, not a multi-turn A2A *interaction
between* two autonomously negotiating agents.

The independent quotation oracle runs typed `Decimal` math, requires
both trusted catalogue and artifact attestations for PASS and rejects
fabricated final success. Its fixture is independent of actual SDK
task/artifact persistence and therefore **does not prove real bilateral
business acceptance**.

The gate refused shared Railway PostgreSQL with
`TEST_DATABASE_NOT_ISOLATED`. Two true PostgreSQL tests skipped.
Dedicated PostgreSQL capacity was denied by the Railway Free-plan limit.
All production/independent DB recovery, full A2A negotiation and ADR-0002
release criteria remain open.
