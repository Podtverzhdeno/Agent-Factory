# Quality gates — Agent Factory

| Gate | Required verification | Status now |
| --- | --- | --- |
| S0 Specification | proposal + delta specs + design + tasks, strict OpenSpec validation, traceability | Pending CLI |
| S1 Owner architectural sign-off | owner-authored or owner-ratified microservice ADR-0002, clear service map, data ownership and GitHub evidence | BLOCKED: awaiting owner |
| S1b Design/security | domain ports, failure states, threat model, tenancy, side effects and ADR | Proposed |
| S2 Code | Ruff + Pyright + pytest + contract/API/migration/security checks | Not implemented |
| S3 Domain | 2 independently evaluated tasks, zero false PASS, negative safety cases, artifact hashes | Not implemented |
| S4 Interoperability | separate A2A client, durable fault injection and no repeated business effect | Not implemented |
| S5 Optimization | immutable baseline, separate validation/holdout, GEPARD regression controls, cost/quality | Not implemented |
| S6 Pilot release | authorization, shadow pilot, approval, signed artifact, rollback evidence, customer acceptance | Not implemented |

## Evidence row schema
AF-REQ | task | code revision | dataset revision | test command | actual output | security review | remaining risks | reviewer sign-off.

Do not mark a check PASS without running it. A green lint check does not prove E2E functionality; GEPARD improvement on train examples does not prove generalization. Critical safety failures veto all metric improvements. Security gates cannot be optimized away.
