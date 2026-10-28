# Launch pack — exactly 9 frontend agents A01–A09

**Readiness:** READY TO COPY THE PROMPTS, **NOT READY TO CLAIM CODE TASKS**. Branch `design/frontend-studio-rfc-20261028` contains a Draft specification PR. I00 common app/contract baseline C0, the atomic GitHub Issue task coordinator and ADR-0002 owner ratification are not verified as delivered. Do not confuse prompt preparation with launched agents or completed app code.


**[Один файл со всеми девятью промптами для раздачи агентам](ALL_9_PROMPTS.md)**. Каждый раздел Axx должен быть отправлен отдельному агенту; не давайте весь файл как одно задание.

## Nine copy-paste prompts

| Prompt | Task / live Issue | Ownership | What this agent will do |
| --- | --- | --- | --- |
| **[A01](A01.md)** | STU-T03 / [#8](https://github.com/Podtverzhdeno/Agent-Factory/issues/8) | Платформа, авторизация и BFF | Аудит реальных API, typed DTO, роли/tenant, capability projection; затем защищённые адаптеры |
| **[A02](A02.md)** | STU-T04 / [#9](https://github.com/Podtverzhdeno/Agent-Factory/issues/9) | UI Kit и 15 графиков | Semantic tokens/SCSS, единые компоненты, 15 ChartKit шаблонов с provenance |
| **[A03](A03.md)** | STU-T05 / [#10](https://github.com/Podtverzhdeno/Agent-Factory/issues/10) | Мастер создания агента | CJM Business Task Package, документы, интеграции, preflight READY и ревизии |
| **[A04](A04.md)** | STU-T06 / [#11](https://github.com/Podtverzhdeno/Agent-Factory/issues/11) | Agents + Mission Control | Каталог, state maps Orchestrator, workflow timeline и причины блокировки |
| **[A05](A05.md)** | STU-T07 / [#12](https://github.com/Podtverzhdeno/Agent-Factory/issues/12) | Playground + Run Inspector | Настоящий sandbox output, artifacts, trace, verified effects, восстановление |
| **[A06](A06.md)** | STU-T08 / [#13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13) | Evaluation + GEPARD + релизы | Независимая оценка, сравнение baseline/candidate, контролируемый выпуск и rollback |
| **[A07](A07.md)** | STU-T09 / [#14](https://github.com/Podtverzhdeno/Agent-Factory/issues/14) | Operator Console 1–5 | Fleet, Workflows/Queues, Builder, Runtime, Registry |
| **[A08](A08.md)** | STU-T10 / [#15](https://github.com/Podtverzhdeno/Agent-Factory/issues/15) | Operator Console 6–10 | Connectors, Artifacts, Evaluation, GEPARD, LiteLLM |
| **[A09](A09.md)** | STU-T11 / [#16](https://github.com/Podtverzhdeno/Agent-Factory/issues/16) | Operator Console 11–15 | A2A, Releases, Observability, Security, Incidents |

**Each linked file is an independent full-length Russian prompt**. Copy its entire contents into a separate agent session. The prompt already includes the repository, spec docs, exclusive allowed paths, what can be researched immediately, what to build after C0/approved lease, exact tests and final evidence format.

## Recommended launch procedure

1. I00 (integrator, **not one of the nine**) opens [I00_INTEGRATOR.md](../I00_INTEGRATOR.md), [task coordinator Issue #18](https://github.com/Podtverzhdeno/Agent-Factory/issues/18), publishes a pinned C0 SHA, typed front-end aliases/contracts, root Next.js skeleton and claim coordinator; never infer this is completed merely because this launch pack exists.
2. In parallel NOW, send **A01–A09** their respective prompt. They may inspect the repository, check actual service APIs, design their own screen/DTO/error/test contract and report precise integration blockers without code writes to a nonexistent C0. Do not claim an Issue while still BACKLOG.
3. After C0 and authorized atomic claim, each agent starts its OWN branch from the same SHA and works only in the directories explicitly listed in its prompt and `WORK_OWNERSHIP_MANIFEST.json`.
4. Have A01 publish stable typed BFF adapters and A02 publish the UI/ChartKit exports first (all others can continue designing and preparing tests). I00 handles shared dependency/layout/API changes rather than nine agents competing over package.json, navigation or global DTOs.
5. The task coordinator maintains authoritative GitHub Issue claim/progress timestamps and generation. After 120 min without **meaningful** progress, agents seek other AVAILABLE tasks first, then investigate PR/commits/CI and request a safe takeover (I00 human approval where required).
6. I00 merges isolated Draft PRs into one integration branch, runs real type/lint/component/auth checks, then 24 CJM E2E scenarios and two independent business fixtures with genuine backend evidence; do not mark “production ready” on documentation/synthetic tests.

## Strict dependencies and default behavior

- **A10 intentionally excluded from the nine**: bilateral A/B builder is a committed advanced product module, with its own existing packet [A10_bilateral.md](../A10_bilateral.md) and [Issue #17](https://github.com/Podtverzhdeno/Agent-Factory/issues/17). Do not delete it from the roadmap; A09 owns only the Operator Console's A2A overview, not A10's shared-agent constructor.
- I00 is distinct from the nine: it owns app root, global navigation, package manifests, shared generated contracts, CI and E2E. No other agent must take those files. If I00 is not available, nine can make **research/preparation output** but cannot safely start shared frontend code under the frozen contract policy.
- Current Issues #8–#16 have initial **BACKLOG / WAITING_FOR_C0**, with null owners and times. The issue state may change; refresh from GitHub before action rather than trusting this README.
- Real source availability outranks UI convenience: when upstream missing, show precise source-limited state, not fake business success.
- Do not begin visual LangGraph editor, microfrontend deployments or A10 advanced builder under these nine prompts.

## Ready-to-send introduction

> Ты получаешь **только один** самостоятельный промпт A0x. Прочти его целиком и выполни текущую фазу: аудит, схемы, состояния, тест-план, запросы I00. Если подтверждены C0 и доверенный lease — реализуй собственный модуль с тестами, в своей ветке/директориях. Не меняй чужие файлы, не присваивай себе задачу комментарием и не заявляй о проделанной интеграции без реального запуска. Сошлись на Issue, SHA, точном статусе, PR, тестах и блокерах.

## Primary reference links

- [Parallel ownership and conflict-free rules](../README.md)
- [Live Issue index](../LIVE_TASK_INDEX.md)
- [Task lease, 2-hour rule, safe takeover](../TASK_LEASE_PROTOCOL.md)
- [I00 / integration/merge gate](../I00_INTEGRATOR.md)
- [CJM requirements and E2E contracts](../../CJM_UI_CONTRACTS_AND_E2E.md)
- [Canonical OpenSpec tasks](../../../../openspec/changes/studio-cjm-parallel/tasks.md)
