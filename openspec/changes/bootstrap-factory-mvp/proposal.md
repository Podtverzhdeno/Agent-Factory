# Change: bootstrap-factory-mvp

## Why

B2B clients need a verifiably working narrow agent, not an untested LLM workflow generator. The factory needs a repeatable way to select minimal capabilities, assemble an agent, verify outcomes, repair failures and publish an auditable result.

## What changes

- Define typed BusinessTask and AgentSpec contracts.
- Add a trust-scored, permission-aware registry of preapproved tools, MCP endpoints and skills.
- Generate specialized agent configurations from a general runtime and minimum necessary capabilities.
- Execute business scenarios in a sandbox and evaluate independent metrics.
- Diagnose failures and attempt bounded automatic repair, including GEPARD prompt/harness optimization.
- Support swappable durable checkpoint/resume and expose an A2A interface.
- Introduce quality, security and human approval gates and release evidence.
- Preserve experimental Soup/LoRA as optional, gated specialization.

## Non-goals

Production payment execution; general-purpose internet MCP installation; automatic training on private customer data by default; free-form auto-deployment of generated executable code; mandatory Pi Durable integration; 1C production integration in this bootstrap.

## Impact

New service skeleton, type contracts, evaluation pipeline, safe tool registry and specifications. **No runtime is implemented by this documentation-only PR.** Subsequent implementation PRs close tasks against actual evidence.

## Definition of pilot outcome

Same factory code builds two distinct narrow agents via config; one deliberate failure produces measurable diagnostic and a passing rerun or BLOCKED; durable recovery from injected interruption; A2A call from a separate client; no unauthorized tool use. Results are recorded with reproducible dataset/model/config versions.

## Open questions

Which first two actual customer task datasets may be used with consent? Which LLM gateway and cost limits? Which runtime passes durability PoC? Which acceptance thresholds match the real business risk? Resolve before real pilot release.
