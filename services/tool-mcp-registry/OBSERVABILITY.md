# Registry v0 observability contract

## Operational telemetry vs. durable audit

`RegistryRequestLoggingFilter` creates a server-generated `X-Request-Id` UUID for every HTTP
request and stores it in a request-local SLF4J MDC until the request exits. The filter must run
before authentication so rejected JWT requests are counted too. A caller-provided
`X-Request-Id` is deliberately **not trusted or echoed**. MDC is cleared in `finally`.

All structured event values are internal, bounded or taken from explicit enumerations:

| Event | Fields | Trigger |
| --- | --- | --- |
| `registry_http_request` | `request_id`, normalized `method`, finite `route`, `status`, `status_class`, `elapsed_ms` | Every HTTP request, including 4xx and 5xx |
| `registry_lifecycle` | `request_id`, `action` (`REGISTERED`, `APPROVED`, `REVOKED`) | Successful state transition only |
| `registry_selection` | `request_id`, `decision` (`SELECTED`/`BLOCKED`), `selected_count`, `denial_count` | Completed `POST /select` |
| `registry_rejection` | `request_id`, fixed `category` (`AUTHORIZATION`, `ABSENT`, `CONFLICT`, `TRUST`, `CAPACITY`, `VALIDATION`, `OTHER`) | Caught typed domain error |

Example (synthetic correlation ID; NOT a successful production test):

```text
event=registry_http_request request_id=cbfc6609-0cba-4697-97c6-ce6edaa5f4de method=POST route=capabilities.select status=200 status_class=2xx elapsed_ms=8
event=registry_selection request_id=cbfc6609-0cba-4697-97c6-ce6edaa5f4de decision=BLOCKED selected_count=0 denial_count=1
```

**Never emit** raw request paths/queries, tenant, subject, JWT, Authorization/cookies, headers,
MCP endpoint, tool ID, manifest description, input/output payload, scope names, error text,
raw denial code, or credentials. Request routing uses a finite classifier and never a raw
URI label, so metrics stay low-cardinality. A parse error before domain dispatch still
produces the HTTP event; it need not produce a `registry_rejection` event.

`RegistryTelemetry` is dependency-free Java 21 and independent of SLF4J; only the HTTP
adapter writes the formatted events. Any new field must first pass a privacy/security review.

**IMPORTANT:** Operational logs are **not an immutable, transactional audit record**.
The current core audit and lifecycle sequence are in-memory. Before production release,
store approval/revocation history and the tenant-local sequence transactionally in
PostgreSQL, enforce retention/backup/legal access policy, and verify restart/fault recovery.
Do not claim that Railway stdout alone provides durable or tamper-proof audit.

## Verification gates

`bash tests/tool-registry/run.sh` runs the JDK core tests, 1060 deterministic telemetry
unit/fuzz assertions and 2400 concurrent correlation operations with `javac -Xlint:all -Werror`.

Maven/MockMvc tests in `RegistryHttpTest` and `RegistryAuthorizedHttpTest` additionally
assert that denied/authorized HTTP calls receive generated correlation IDs and that
sampled Logback events contain no malicious headers, tenant/capability names or bearer
secrets. These tests are **not verified until an online Java/Maven CI runner executes**
`mvn -f services/tool-mcp-registry/pom.xml -B clean verify` on the exact PR revision.

Operational acceptance on Railway also requires a real HTTP request, inspectable trace
ID, and post-deploy error-rate/latency checks. No new Railway service has been deployed
by this change.

## Operator runbook

- Investigate 5xx or rising latency by `event=registry_http_request`, `route`, and `status_class`.
- Correlate a safe request with `request_id`, then check the typed `registry_rejection`
  `category`; do not request raw JWTs or manifest payloads from users.
- Investigate unexpected `REGISTERED`/`APPROVED`/`REVOKED` ratios using tenant-restricted
  PostgreSQL audit **after** persistence is implemented; request logs cannot establish
  who performed an action.
- Set appropriate Railway log-retention/access permissions; ensure alerting does not
  attach sensitive HTTP request bodies, Authorization headers, or private network URLs.
- If logs are missing for denied JWTs, verify the request filter executes before the
  Spring Security chain and that Info logging has not been disabled.
