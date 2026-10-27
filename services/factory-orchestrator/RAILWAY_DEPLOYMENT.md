# Agent Factory workstream 01 — Railway deployment proposal

**Status:** PREPARED / NOT RELEASED. This is an isolated service proposal, not owner
ratification of ADR-0002. Do not interpret an HTTP 200 from `/healthz` as
production readiness, Evaluation provenance, or working real upstream services.

## Identified Railway infrastructure (2026-10-27)

- Project: `ed32802c-7f84-47c3-b744-45e1fe2e6236`
- Project dashboard: https://railway.com/project/ed32802c-7f84-47c3-b744-45e1fe2e6236
- Name: `adequate-respect`
- Environment: `production` (`eacbc53d-a71c-4078-ad68-7e85329d2ab4`)
- Existing service: `Agent-Factory` (`b0239f26-72d9-4a6e-a0d0-9a429ea0f384`)
- GitHub source: `Podtverzhdeno/Agent-Factory`, currently branch `main`.
- First deployment `90730d91-ec61-434a-84a3-effb584cb764`: **FAILED**.
  Build logs: `Railpack could not determine how to build the app`;
  its source checkout contained **README.md only**. This is not a Java compile failure.
- No PostgreSQL service, volumes, publicly exposed domain, or build secrets
  were present when inspected.

## Monorepo Docker image

`services/factory-orchestrator/Dockerfile` is a multi-stage Java 21 build.
Railway must keep repository root as the build context because Maven requires
the sibling `services/agent-store` and shared `tests/control-plane`.
Set custom Dockerfile path to
`/services/factory-orchestrator/Dockerfile`; do NOT set root directory to
`/services/factory-orchestrator`, which would hide these required sources.

The Maven image packaging step compiles sources and tests but does **not**
execute the full acceptance suite: Testcontainers requires an external
Docker-enabled CI runner. Release only after a matching exact PR SHA runs:
`EXPECTED_HEAD_SHA=<sha> bash tests/control-plane/run-acceptance.sh`.
A production deploy must point to the same, reviewed code revision.

The runtime uses non-root UID 10001, Java 21 JRE, Railway's `PORT` environment
variable and Java's memory-percentage limit. Public `GET /healthz` returns only
`{"status":"alive"}` (liveness, not readiness). All workflow and event API
routes still require validated service/user JWTs.

## Mandatory deployment gates

1. Owner ratifies ADR-0002 with traceable GitHub evidence and defines the
   service topology, persistent database owner, A2A exposure and API consumers.
2. Execute exact-SHA Maven/JUnit/Spring Security, PostgreSQL Testcontainers and
   independent Builder/Evaluation/GEPARD contract security tests.
3. The current production branch `main` does **not** contain this PR's Java
   application. Do not accept staged Railway config or switch its repo branch
   until source is approved and quality gates pass.
4. Configure a real trusted JWT issuer/audience, runtime token provider and
   independently verifiable Evaluation evidence; no dummy JWTs, fake credentials,
   public PostgreSQL TCP proxy, or anonymous command ingress.
5. Provision a dedicated private PostgreSQL service in the ratified data
   ownership boundary, stage/apply forward-only migrations V1 and V2, and
   inject credentials using Railway service-to-service variable references.
6. Set `/healthz` liveness check; separately verify DB readiness, actual
   authenticated HTTP endpoint behavior, durable outbox recovery, and monitored
   canary/rollback. Do not silently turn a POC into a public production endpoint.

A pending staged Railway config is a draft proposal only. No successful
runtime deployment or production acceptance is claimed.
