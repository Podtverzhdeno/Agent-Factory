# Change: a2a-bilateral-evaluation

## Why

A verified agent may pass isolated tasks yet fail a real A2A dialogue involving independent organizational goals, conflicting rules, files, clarification, retries and asynchronous outcomes. The factory needs independent tests of the *cross-organizational operation*, while preserving each firm's privacy, autonomy and approval authority.

## What changes

- Define versioned two-party A2A scenarios using separately owned approved Business Task Packages and agent versions.
- Execute authorized A2A dialogues in a sandbox, including real protocol Tasks/Messages/Parts/Artifacts and fault injection.
- Evaluate agent A, agent B and their verifiable joint business outcome independently; capture cost, round trips, formatting and policy failures.
- Feed sanitized findings into Orchestrator-directed GEPARD optimization of A or B, rerun cross-play with unchanged partners and held-out cases before release.
- Make consent, confidentiality, role separation, and independent per-tenant release gates first-class invariants.

## Scope

P1 pilot experiment after basic single-agent build/evaluation and A2A invocation are implemented. No new deployable microservice is mandated: first propose Evaluation-owned A2A simulation workers with explicit Orchestrator commands.

## Non-goals

Autonomous negotiation of real binding contracts, payments, price coordination between competitors, sharing partner's private prompts/traces, exposing sealed gold test answers, mandatory Soup training, or automatic cross-tenant updates without mutual authorization.

## Expected pilot evidence

Two independently configured synthetic buyer/supplier agents execute diverse A2A cases; at least one diagnosable communication error leads to a candidate update and independent re-evaluation. Record per-organization quality, verified joint outcome and hard security gates. Demonstrate robust cross-play against frozen partner version, not only a jointly tuned pair.

## Architecture owner

@Podtverzhdeno must decide service boundary, milestone priority, exchange-consent policy and release authority in ADR-0002 / follow-up ADR. This change is a DRAFT proposal, not an approved implementation.
