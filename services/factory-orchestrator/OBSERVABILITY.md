# Control Plane — operational logging and acceptance

Status: private, fail-closed development/smoke profile. This page is an operational
aid **not** an ADR approval, SIEM certification, production SLA or production go-live.

## What is logged

The Control Plane emits single-line, low-cardinality key/value events through
`java.util.logging`. Search in Railway **service logs** for
`event=control_plane.outbox` and `event=control_plane.lifecycle`:

- `control_plane.outbox`: `outcome=ACKNOWLEDGED` after durable acceptance,
  `RETRY_SCHEDULED` after persisted retry attempts, `BLOCKED` for final
  remote/contract failures, `SUPERSEDED` for late results ignored after state
  changes. Fields: fixed action, opaque workflow/operation/correlation references,
  bounded attempt count, allowlisted failure class.
- `control_plane.lifecycle`: `PUBLISHED` after a durable notification receipt,
  `PUBLISH_FAILED` when a publisher throws, `SUPERSEDED` when another process
  has already acknowledged the record. Fields: fixed state-transition enums,
  opaque workflow/event/correlation references, bounded sequence.

**A success healthcheck is only process liveness.** A successful notification or
remote-command log is evidence of that *specific operation*, not of production
readiness, safety attestation or upstream correctness.

### Privacy/security properties

Do **not** log raw bearer tokens, request/response JSON, URLs, tenant IDs,
workflow IDs, artifact references, evaluation results, secret headers, exception
messages or stack traces of network failures. `workflow_ref`,
`operation_ref`, `event_ref`, `correlation_ref` are hexadecimal SHA-256
truncations with a **random per-process salt**. They correlate logs within one
process; they deliberately **change across deployments/restarts**. They are
**not** customer-visible IDs or durable tracing identifiers. Persisted
`cp_workflow`/event inbox/outbox and the authorized workflow audit API are
the authoritative cross-restart record.

Only preapproved error codes are logged; arbitrary remote error messages
are classified as `OTHER_FAILURE`. Avoid changing logging to include
`exception.getMessage()`, authorization headers, telemetry attributes from
untrusted payloads, or full workflow objects.

### Traffic/volume

Outbox ACK and retries are INFO; permanent failures are WARNING; stale
callbacks are FINE (debug-level). Lifecycle publishes are INFO, publisher
failures are WARNING, superseded receipts are FINE. Do not enable FINE in
production without volume controls and a defined retention policy. Do not
enable logging of whole HTTP bodies.

### Diagnosing failures

1. Filter `event=control_plane.outbox outcome=BLOCKED`; inspect the
   `code` and `action`, not customer content.
2. Repeated `RETRY_SCHEDULED` events indicate an upstream outage or
   misconfiguration. No framework-level automatic HTTP redirect is allowed.
3. Search `event=control_plane.lifecycle outcome=PUBLISH_FAILED` for
   notification-relay outages. At-least-once retries require consumer
   idempotency.
4. Correlate process-local opaque refs while the process is running. For
   historical diagnosis across restarts, use the **authorized** workflow
   audit and stored command receipts instead of guessing matching hashes.
5. Alerts should be based on counts/rates of `BLOCKED`, `PUBLISH_FAILED`,
   and the age of pending outboxes; do not alert using raw tenant names or
   ephemeral process-local refs.

## Executable evidence

The Railway smoke Dockerfile builds with Java 21 + disposable PostgreSQL 16
and executes `mvn -B -ntp -f services/factory-orchestrator/pom.xml clean verify`.
It then runs `tests/control-plane/verify-surefire.py` to reject missing, skipped,
failing or unexpectedly reduced required JUnit suites. Tests include:

- `ControlPlaneTelemetryTest`: 9 outbox outcome/secret-redaction cases.
- `LifecycleTelemetryTest`: 4 notification replay/failure/redaction cases.
- PostgreSQL, HTTP, Spring security, negative profile startup, and domain tests.

Only cite results for the **exact deployed SHA** shown in Railway. Keep ADR-0002
pending, PR Draft and production JWT/service credentials disabled until separate
owner decisions and integration acceptance.

## Railway-native tracing and alert watch (2026-10-27)

The `Agent-Factory` Railway service now has **tracing enabled** and
**automatic instrumentation active**. This is a control-plane-only service
setting; it does **not** automatically turn on tracing for agent-engine,
PostgreSQL, Builder or Evaluation. Verify actual app/exported spans through
Railway tracing coverage, not from the enabled switch alone. At initial
activation the verified `spanCount` was **0**, and no cross-service trace
had been captured. Do not treat /healthz or an empty tracing view as proof
of real agent-to-agent instrumentation.

An independent **hourly conditional health check** has been configured
to read Railway service health, deployment failures, CPU/memory usage and
the `BLOCKED` / `PUBLISH_FAILED` operational log outcomes. The watch
sends a notification only on a confirmed new problem and does not require
creating a public HTTP domain or an additional paid monitor service.

**Operational limitations and alert rules:**
- The monitoring agent checks **hourly**, not continuously: failure
  detection can lag the incident. For production SLOs use a
  continuously running monitoring backend with tested on-call delivery.
- Treat `FAILED`/`CRASHED` current deploys, failing healthchecks,
  persistent `BLOCKED` actions, repeated `PUBLISH_FAILED`, and
  persistent saturation as candidates for human action.
- Exclude synthetic/fail-closed expected errors originating from build
  regression tests; compare deployment SHA and log type.
- Confirm at least one actual app-exported trace and test notification
  delivery before treating distributed tracing or alerts as
  production-ready. The test service currently has no public domain.

## Cross-service E2E evidence boundary

`JdbcPersistenceIntegrationTest.completeBuildEvaluationGepardRetestLifecycleSurvivesRestarts`
tests the full **Builder -> Evaluation -> GEPARD -> re-Evaluation -> VERIFIED**
contract against real loopback HTTP peers and PostgreSQL 16. Every
stage recreates the workflow ledger, agent registry and outbox relay;
the two JDBC adapters share one transaction scope. It checks that each
accepted command is not resent after a restart and a single candidate
persists as VERIFIED. This is strict **synthetic-peer** contract E2E, not
proof that deployed Agent Engine, real GEPARD/Evaluation providers, JWT
identity, or external effects have been tested together.
