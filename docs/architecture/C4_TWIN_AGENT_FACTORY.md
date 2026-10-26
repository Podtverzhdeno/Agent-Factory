# C4 L2/3 — Twin-Agent Factory, Adaptive Harness and Model Benchmark

Status: DRAFT for owner architectural approval. Matches docs/architecture/TWIN_AGENT_HARNESS_RFC.md. Generated design, not implementation.

## Container relationships

~~~mermaid
flowchart TB
    BA["Org A BTP & files"]
    BB["Org B BTP & files"]
    IN["Task Intake / File Processing"]
    K[("Kafka lifecycle events")]
    O["Factory Orchestrator · Spring Boot"]
    B1["Builder Worker A · Python"]
    B2["Builder Worker B · Python"]
    T["Tool / MCP Registry"]
    A["Agent A · Python LangGraph"]
    B["Agent B · Python LangGraph"]
    EV["Evaluation + A2A Simulation · Python"]
    G["GEPARD Optimizer · Python"]
    SO["Soup · Python GPU Optional"]
    MO["Model Cost–Quality Benchmark · Evaluation capability"]
    L["LiteLLM Gateway"]
    ST["AgentStore · version/artifact context"]

    BA --> IN
    BB --> IN
    IN -->|"validated BTP IDs"| K
    K --> O
    O -->|"explicit REST build A"| B1
    O -->|"explicit REST build B"| B2
    B1 <-->|"authorized tools"| T
    B2 <-->|"authorized tools"| T
    B1 -->|"AgentSpec A0"| A
    B2 -->|"AgentSpec B0"| B
    O -->|"explicit A2A test"| EV
    EV <-->|"authenticated A2A"| A
    EV <-->|"authenticated A2A"| B
    A <-->|"bilateral protocol tasks"| B
    O -->|"diagnose and optimize"| G
    G <-->|"A candidate harness"| A
    G <-->|"B candidate harness"| B
    O -->|"authorized fine-tuning"| SO
    O -->|"independent model comparison"| MO
    MO -->|"matched candidate tests"| EV
    A --> L
    B --> L
    G --> L
    MO --> L
    B1 & B2 & EV & G & SO & MO --> K
    O -->|"approved tenant releases"| ST
~~~ 

Two Builder workers are instances of ONE independently deployable Builder implementation, not new bespoke services per tenant. Model Benchmark is a separately testable Evaluation capability; an independent microservice is NOT decided. AgentStore is a distinct version ownership context, not yet an owner-approved separate deployment.

## Model policy experiment

- Baseline pair: A0(model A baseline), B0(model B baseline).
- Candidate A only: A1(cheaper/step-routed model), B0.
- Candidate B only: A0, B1.
- Joint: A1, B1.
- Further frozen/unknown counterpart variants and hidden holdouts verify robustness.
- Eligibility: tool/JSON/context/residency/cost requirements; no silent tool-capability downgrades.
- Promotion requires independent quality non-inferiority evidence, hard policy gates for both firms, approved tenant-specific release conditions, and a demonstrable reduction in total cost per correctly completed joint operation (including retries/tool/fallback costs).
- Insufficient data means INCONCLUSIVE, not proven equivalent.
- LiteLLM routes approved models and records attributable costs, but does not make the quality-gating decision.

## Harness non-goals

GEPARD cannot rewrite unauthorized MCP tools, grant new permissions or optimize hidden model reasoning. Durable checkpointing and long-term memory are distinct responsibilities from the initial agent build, not interchangeable with optimizer/fine-tuning. No confidential cross-tenant prompt/memory sharing.
