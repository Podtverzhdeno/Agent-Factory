# MVP / Pilot — product contract

Status: PROPOSED. No customer-ready feature exists yet.

**Customer outcome:** take a constrained B2B task, assemble minimum sufficient agent from pre-approved tools/MCP/skills, execute it in sandbox, independently evaluate, repair in bounds, and produce verified release or explicit BLOCKED reason.

## Actors
Factory Operator (inputs business task and acceptance); Domain Expert (gold examples, business approvals); Integration Owner (credentials, tool manifests, access); Authorized A2A client (invocation).

## Task package and file readiness (required for P0)

The user must be able to create a **Business Task Package** with typed business inputs and expected outputs, approved workflow/rules, file-based examples and templates, connector requirements, safety bounds and testable acceptance. Upload support must include XLSX, PDF, DOCX, CSV, JSON/API contracts; formats are implementation acceptance requirements, not a claim of current support. Parsing must be safe, provenance-aware and asynchronous when expensive. Examples for Builder/GEPARD and sealed independent holdouts for Evaluation remain isolated. The factory must ask for missing rules, permissions or gold results instead of fabricating instructions or pass metrics.

## File-backed task definition

P0 requires a typed Business Task Package: objectives, business rules, input and output file schemas, versioned approved examples, authorized integration needs and measurable acceptance tests. XLSX, PDF, DOCX, CSV and API-contract inputs must be processed with provenance. Builder/GEPARD can see approved examples; sealed gold acceptance cases remain exclusive to Evaluation. Unclear rules or missing permissions prevent build readiness.

## P0 — core MVP
BusinessTask schema; verified Tool/MCP Registry; minimal-capability planner; immutable AgentSpec compiler; isolated runner; independent business evaluators; failure diagnosis; bounded repair controller; evidence/audit; explicit BLOCKED/FAILED/VERIFIED status. Only synthetic or authorized datasets.

## Owner-selected common inference gateway
LiteLLM Proxy is included in the MVP as the centralized, tenant-scoped model gateway for Agent Runtime and GEPARD. Provider keys remain centralized; independent budget/credential/rate-limit tests are part of pilot quality criteria. A gateway with missing budget persistence is not considered ready.

## P1 — essential demo
GEPARD prompt/harness optimizer (isolated, baseline + held-out tests); swappable durable runtime (crash/resume and idempotency tests); independent A2A client/server exchange; human release gate; operator-facing API/CLI.

## P2 — research, not first release
Soup/LoRA special training, experimental Pi Durable adapter benchmark vs Python-native durable runtime, A2A payment/ACT links, new unknown MCP auto-installation, complex distributed UI/marketplace.

## Two acceptance journeys
**A. Chemical RFQ**: read chemical request -> catalog/quality/certificate lookups -> produce draft response for human approval, no unverified substitutions or live sending.
**B. Certificate verification**: ingest document references -> verify permitted sources -> return discrepancy report + audit evidence, no false legal verification promise.

One codebase SHALL generate two AgentSpec configurations with different tool sets based on task description and allowed scopes. One deliberately broken scenario SHALL result in automatically diagnosed and repaired improvement OR an explicit, accurate BLOCKED reason.

## Boundaries
No automatic deployment of generated executable code to production; no unknown MCP with production secrets; no irreversible finance/order operations without human approval. A2A interoperability required; production integration to a third-party marketplace not promised.

## Metrics (provisional until gold dataset is agreed)
Safety hard gates 100%; zero false PASS on intentionally impossible tasks; two task types independently passed; fault-injection restart without duplicate business effects; optimizer measured against immutable baseline incl. tool-use correctness, quality, latency and total cost per correctly completed task.

## Business hypothesis
Client buys independently verified task outcome, reuse and faster rollout. Candidate revenue: onboarding/pilot + recurring runtime, monitoring, optimization + optional private models. Prices and ROI are NOT validated. Pilot interview must confirm actual volume, authorized data, pain, owner, baseline time/cost and willingness to pay.

## Proposed P1 twin-agent and model-routing benchmark

Twin builds have independent corporate inputs, code-sharing Builder workers and separate agent runtimes. Initial harness includes persistent checkpoints, short-term and long-term memory policies, tool/MCP permissions, ReAct/action graph and A2A. Candidate optimization tests prompts, compatible tool descriptions, memory/retrieval/graph behavior and per-step LiteLLM model choices. Model replacement is accepted only after quality non-inferiority, per-party safety gates and lower end-to-end cost per successfully completed A2A operation. Publish tenant-specific immutable versions into proposed AgentStore only after independent approval. Architecture is not yet owner-ratified; Soup remains optional, Pi Durable R&D only.

## Proposed P1 bilateral A2A pilot (not a currently implemented feature)

With each participating organization's permission, create two independently configured buyer/supplier agents and evaluate the end-to-end A2A business task. Report per-tenant quality and privacy constraints, shared operation completion, messages, latency, cost and output Artifacts. Optimize A and B separately using authorized dialogue findings; replay candidate A1 with frozen B0, candidate B1 with frozen A0 and A1/B1 before any release. No sharing of proprietary prompts or sealed holdout answers; production side effects are not enabled. See docs/architecture/A2A_BILATERAL_EVALUATION_RFC.md. This feature is an optional P1 pilot, not part of P0 deliverability.
