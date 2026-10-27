# Agent 05 — CURRENT local verification snapshot, 27 Oct 2026

**Branch:** `agent/05-quality-engine`, PR #2; workstream scope unchanged.

- `pytest -q tests/quality-engine -W error::ResourceWarning` — **117 passed, 3 skipped** (Python 3.13.5). Three skips are the opt-in *real* PostgreSQL server, live LiteLLM Proxy, and live DSPy/GEPA inference, all still OPEN.
- `pytest -q tests/quality-engine --cov=quality_engine --cov=gepard_optimizer --cov-report=term -W error::ResourceWarning` — **117 passed, 3 skipped, 93% statement coverage** (1,181 statements, 79 missed).
- `python -m compileall -q services` — success. These checks ran on the locally staged Python sources; the currently configured GitHub SDD workflow does not run this Python suite on the exact PR commit.

**Newly verified beyond earlier snapshots:** fenced lease heartbeat sustains long-running Evaluation and denies obsolete workers; separate read-only Runtime HTTP audit client with bounded body, TLS requirement, strict typed schema and service authentication; **real loopback TCP** to a locally simulated Ed25519-signing Runtime → Evaluation → SQLite job store → outbox; signature now covers `evaluation_run_id`, and attempts to replay old run evidence fail closed; signer expiry/revocation can be checked via an injected current key resolver; actual DSPy GEPA five-argument metric interface checked against public DSPy docs and negative-tested.

**Critical distinctions:** The loopback server is a test double, **not Agent 04 Runtime**. Real external PostgreSQL/Kafka/LiteLLM/DSPy, service identity, signed producer, production KMS, shared CI and whole-factory E2E remain unverified. ADR-0002 requires owner decision. No production acceptance or merge is claimed.

---

## Detailed previous verification records (historical snapshots)

Updated 2026-10-27. Workstream branch: agent/05-quality-engine. PR #2.
**Scope:** local component verification and explicitly separated external integration gates.

## Historical component verification before the latest hardening

- Python 3.13, pytest 9, SQLAlchemy 2, cryptography 46, FastAPI/httpx
- `pytest -q tests/quality-engine -W error::ResourceWarning` → **81 passed, 3 skipped** (no warnings)
- `pytest --cov=quality_engine --cov=gepard_optimizer --cov-report=term -q tests/quality-engine` → **81 passed, 3 skipped, 94% statement coverage** (961 statements; 53 missed, before warning-only test fixture cleanup)
- `python -m compileall -q services` → **passed**
- Skipped (not counted as passing): opt-in REAL PostgreSQL test (no dedicated PG test service/driver), live DSPy GEPA via LiteLLM (no approved budget/API), and live LiteLLM Proxy smoke (no approved endpoint/credentials).
- GitHub Actions checks in this repo currently validate OpenSpec/SDD, NOT this executable Python suite. CI green alone is not Quality Engine E2E proof.

## Domain and security evidence

- RFQ and certificate fixtures score real structured business artifacts, required authorized tool calls and audited effect proofs; fluent false completions fail
- ReAct observable transitions and short/long memory provenance, TTL and tenant violations are scored, including hard security veto
- Evaluation's sealed gold never passes to PublicRunCase/Runtime or GEPARD; versioned train/holdout source collisions and denied access tested
- Signed Runtime evidence HMAC adapter binds tenant, spec, dataset, case, trace and observed tool effects; tampering is blocked. **Production key management/mTLS and authenticated Runtime audit producer are NOT connected**
- SQLAlchemy DatasetVault persists immutable case records; with strict encryption configured it stores AES-256-GCM ciphertext (AAD includes tenant/version/case). Database-level auth and key management still required
- SQL-backed job workflow recovers across application instances, uses atomic lease claim/fencing, retry limit and transactional completion outbox; stale worker cannot commit
- Outbox Kafka transport port sends messages only when ACKed; broker errors leave events pending. At-least-once delivery requires downstream event_id deduplication. Real Kafka broker NOT used
- LiteLLM httpx client tests the real HTTP request format via MockTransport with model allowlist, TLS policy and safe failures; actual proxy/provider cost metering NOT tested
- Model benchmark: paired business outcomes, correct-task cost incl retries/tool/fallback, conservative one-sided loss bound, capability/residency/safety rules, holdout evidence required; INCONCLUSIVE on insufficient evidence
- GEPARD typed immutable candidate adapter + DSPy GEPA invocation wiring with injected fake DSPy; real DSPy package and reflection LM not available in local environment, so real optimization is NOT verified
- One synthetic fail → candidate patch → holdout retest checks the control flow but never releases a production agent

## Remaining mandatory integration acceptance

1. Owner ratifies ADR-0002 (service topology, IAM, network, deployment and data ownership). Agent #5 cannot approve it.
2. Workstream 04 issues signed authoritative runtime audit/typed tool-effect evidence. Proposed contract in services/evaluation/CONTRACT_CHANGE_REQUEST.md; handoff added to PR #3.
3. Live PostgreSQL integration: `tests/quality-engine/test_postgres_integration.py` (opt-in), isolated Compose recipe at `services/evaluation/POSTGRES_INTEGRATION.md`; not run locally.
4. Actual Kafka broker with authenticated producer/consumer, outbox ack/fail/replay and event_id dedup. Current KafkaPythonTransport exercised via ACK fake only.
5. Actual LiteLLM Proxy (approved budget persistence + provider pricing), credential provisioning, cost reconciliation and rate-limit test. Cannot claim token savings from mocks.
6. Actual DSPy GEPA optimizer run through approved LiteLLM Proxy with training/validation data, budget and a separately sealed holdout.
7. Distributed identity, KMS keys, database migrations and reliable worker deployment/restart/observability in approved topology.
8. Unified end-to-end two-business-task pipeline with 01–04 components and rollback/release evidence.
9. Integration owner adds cross-workstream Python test job to shared GitHub CI. Agent 05 cannot edit .github per workstream ownership.

**Status: COMPONENT VERIFIED; CROSS-SERVICE/PRODUCTION INTEGRATION BLOCKED.**
Never mark main project-wide requirements fully closed from these test doubles or skipped tests.


## Security review addendum — encryption-by-default

`SqlDatasetVault` fails at construction without an injected tenant cipher unless explicitly configured `require_encryption=False` for isolated tests. AES-256-GCM authenticates tenant/version/case in AAD. Wrong key, tampered ciphertext and swapped record identity are rejected. This is application encryption, not a replacement for KMS, key rotation, PostgreSQL IAM, backup controls or mTLS.

The latest strict local run remains **81 passed, 3 skipped** using `pytest -q tests/quality-engine -W error::ResourceWarning`, with no reported warnings. The skipped real PostgreSQL test is not counted as passed.

## Executable opt-in external integration checks

- `tests/quality-engine/test_postgres_integration.py` — PostgreSQL schema, tenant gold, recovery. Isolated Docker recipe in `services/evaluation/POSTGRES_INTEGRATION.md`. No dedicated PostgreSQL binary is installed in this execution environment.
- `tests/quality-engine/test_litellm_live_optin.py` — real HTTP Proxy smoke; requires approved model, endpoint, credentials and `AF_QUALITY_ALLOW_PAID_INFERENCE=YES`. It measures response/usage; does not certify price-quality.
- `tests/quality-engine/test_gepa_live_optin.py` — genuine DSPy GEPA compile with a synthetic training/validation corpus and a LiteLLM reflection model, capped to 8 metric calls; requires separately authorized credentials and the optional `dspy` package. Not executed in this environment.

**Result of latest strict local run:** 81 PASS, 3 SKIP, no ResourceWarnings. All skipped external integrations remain OPEN, not silently treated as proof.

## New deterministic regressions and strict local run (2026-10-27)

Exact local source stage, Python 3.13.5:
- `python -m pytest -q tests/quality-engine -W error::ResourceWarning` → **98 PASSED, 3 SKIPPED** (no ResourceWarnings).
- `python -m pytest --cov=quality_engine --cov=gepard_optimizer --cov-report=term-missing -q tests/quality-engine -W error::ResourceWarning` → **98 PASSED, 3 SKIPPED; 95% coverage** (1,013 statements; 55 missed).
- `python -m compileall -q services` → exit code 0.
- SKIPPED integrations remain real PostgreSQL, live LiteLLM Proxy and real DSPy GEPA (not counted as successes). GitHub's shared workflow checks SDD/OpenSpec only, not these Python tests.

New verified fixes:
- Durable Evaluation no longer attempts to store tuning-only PASS as a release decision and leave a worker RUNNING; it commits BLOCKED/INDEPENDENT_HOLDOUT_REQUIRED and one sanitized outbox event.
- SQL store prevents FAILED status with a contradictory positive evaluator result.
- Model benchmark requires an absolute minimum successful-operation rate for BOTH baseline and candidate; two equally unreliable cheap models fail the gate.
- LiteLLM HTTP adapter rejects unapproved provider model substitution, negative/noninteger tokens and nonfinite/negative response costs.
- Cost-quality PASS now requires an injected trusted evidence verifier; a self-declared string saying holdout yields INCONCLUSIVE. Production service must implement that verifier against evaluator-owned signed source evidence, rather than a test lambda.
- Added Ed25519 verification-only Runtime audit adapter, tenant-bound public keys, forged signature detection and full signed-audit-to-durable-workflow smoke test. Production Runtime audit producer/key rotation/mTLS remain cross-team work.

The historical phase used local mocks and SQLite. The later TCP test above exercises a real loopback connection to a synthetic Runtime, not a deployed cross-service producer.
