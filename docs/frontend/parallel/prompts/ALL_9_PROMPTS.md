# Agent Factory Studio — all nine independent ready-to-copy prompts

**Important:** THESE ARE NINE SEPARATE ASSIGNMENTS. Give only one Axx section to each separate coding agent. Do not paste the entire file into one agent expecting it to implement all scopes. The spec is not a launched task. Shared C0 base and trusted GitHub claim coordinator remain prerequisites for coding.

[Launch instructions and live Issue links](README.md) · [Ownership rules](../README.md) · [Task lease protocol](../TASK_LEASE_PROTOCOL.md)

---

<!-- BEGIN PROMPT A01 -->

# Промпт A01 — Платформа, BFF, авторизация и возможности

Ты отвечаешь за **Платформа, BFF, авторизация и возможности**. Task **STU-T03**, [Issue #8](https://github.com/Podtverzhdeno/Agent-Factory/issues/8), техническое задание `docs/frontend/parallel/A01_platform-bff.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/server/**`
- `apps/studio/src/shared/api/**`
- `apps/studio/src/shared/auth/**`
- `apps/studio/src/shared/capabilities/**`
- `apps/studio/src/app-shell/**`
- `apps/studio/app/api/studio/**`
- `apps/studio/app/(auth)/**`
- `apps/studio/src/features/platform/**`

## Прямо сейчас — исследование и подготовка без C0

1. Проверь предложенные Studio DTO и реальные OpenAPI Control Plane, Registry и остальных сервисов. Составь таблицу `route → владелец backend → доступность API → auth/scope → схема → ошибки`; не считай предложенный endpoint реально существующим.
2. Проверь, какие именно данные и механизмы OIDC/CSRF/tenant есть в репозитории. Отдельно запиши проблемы отсутствующего IAM, Task Intake, signed evidence, release, GEPA и биллинга.
3. Спроектируй стабильный публичный typed API для A03–A09 и точную модель `AVAILABLE/DEGRADED/DISABLED/PLANNED` с различением design, component tests, staging, production. Определи требуемые типы SourceStamp, SafeError, AllowedAction.
4. Подготовь тест-матрицу 401/403/409/429/500, смены tenant, кешей, неизвестных enums, повторной отправки команды и недоступности сервиса. Подготовь запросы I00 на общие aliases/сессию/C0.

**Первый измеримый результат:** Таблица реальности backend API + предложенные exported TS interfaces для всех остальных агентов; затем безопасный BFF в своих каталогах. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Реализуй защищённые серверные Route Handlers и адаптеры к подтверждённым реальным API внутри `src/server`, без внешнего доступа браузера к Java/Python microservices; недоступные источники должны возвращать отказ/UNAVAILABLE, не mock-success.
2. Реализуй typed browser client с source timestamp/revision/completeness, безопасную ошибку, tenant-keyed cache и разрешённые действия; прозрачное получение capability projection.
3. Добавь тесты на межтенантные прямые URL, потерю прав, запросы идемпотентности, отсутствие секрета в bundle, отказ неподтверждённым release/PASS. Для операторских mutation routes — явный allowlist schemas, не generic execute.

## Приёмка и тесты

CJM-E2E-006/008/009/018/022; реальные авторизационные и transport unit тесты; проверки неизвестных состояний и no-secret leak.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A01_platform-bff.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A01 -->

---

<!-- BEGIN PROMPT A02 -->

# Промпт A02 — Дизайн-система, SCSS Modules и графики

Ты отвечаешь за **Дизайн-система, SCSS Modules и графики**. Task **STU-T04**, [Issue #9](https://github.com/Podtverzhdeno/Agent-Factory/issues/9), техническое задание `docs/frontend/parallel/A02_design-charts.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/shared/ui/**`
- `apps/studio/src/shared/styles/**`
- `apps/studio/src/shared/charts/**`
- `apps/studio/src/features/chart-showcase/**`

## Прямо сейчас — исследование и подготовка без C0

1. Проанализируй экраны CJM и составь минимальную унифицированную дизайн-систему: цветовые semantic tokens, плотность, типографика, spacing, радиусы, состояния ошибок, темы и responsive.
2. Опиши public API компонентов Button, Input/FormField, Dialog, DataTable, StatusBadge, Timeline, Tabs, FileUpload UI, PageState, SafeTooltip, ChartView. Заранее объяви интерфейсы остальным агентам, не меняя чужие файлы.
3. Спроектируй 15 типов графиков из STUDIO_BOXED_PRODUCT_FEATURES, data contract, provenance, table fallback, empty/partial/error; оцени Apache ECharts как один движок, а не набор несовместимых библиотек. Перед добавлением зависимости оформи DEPENDENCY_REQUEST для I00.
4. Запланируй а11y-матрицу, клавиатуру, focus, screen reader, reduced motion, светлую/тёмную тему и бюджет большого набора данных.

**Первый измеримый результат:** Типизированный UI-kit контракт и список графиков с требованиями к данным; после C0 — reusable компоненты и ChartKit. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Создай токены CSS custom properties, SCSS Modules, переиспользуемые UI-компоненты с typed props, тестами состояний, доступностью и RU/EN текстовыми ключами.
2. Создай единый ChartKit на 15 визуализаций через один адаптер и discriminated union, с lazy-load, таблицами, timestamp, units, samples, permission states; synthetic preview только в chart-showcase, никогда как бизнес-метрика.
3. Сделай демонстрационные fixture/stories для каждого компонента и графика; компонентная регрессия и проверка больших серий. Не редактируй корневые стили/layout, попроси I00 импортировать их.

## Приёмка и тесты

CJM-E2E-013/016/019/023; 15 chart variants, а11y/keyboard, empty/partial/real-series gate, SCSS и bundle impact.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A02_design-charts.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A02 -->

---

<!-- BEGIN PROMPT A03 -->

# Промпт A03 — Мастер создания агента и Business Task Package

Ты отвечаешь за **Мастер создания агента и Business Task Package**. Task **STU-T05**, [Issue #10](https://github.com/Podtverzhdeno/Agent-Factory/issues/10), техническое задание `docs/frontend/parallel/A03_task-intake.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/task-intake/**`
- `apps/studio/app/[locale]/w/[workspaceId]/agents/new/**`
- `apps/studio/app/[locale]/w/[workspaceId]/tasks/**`

## Прямо сейчас — исследование и подготовка без C0

1. Детализируй реальный процесс RFQ и проверки сертификата как два различных бизнес-фикстура на ОДНОМ мастере; распиши каждое поле и обязательный результат.
2. Уточни пошаговый UI: цель/процесс, документы и примеры, инструменты/разрешения, критерии приёмки, подтверждение READY. Отдельно состояния восстановления черновика и ревизионного конфликта 409.
3. Составь матрицу файлов PDF/XLSX/DOCX/CSV/JSON/OpenAPI: назначение, hash, provenance sheet/page/row, проверка прав, PII, rejected/ingesting/ready. Не придумывай запущенный Task Intake.
4. Проверь разницу между доступными Registry API и предложенными Task Intake endpoint; создай список недостающих контрактов для A01/I00.

**Первый измеримый результат:** Завершённый field-level CJM мастера и отсутствие критичных неопределённостей для двух разных бизнес-задач. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Реализуй мастер с сохранением черновика, нормализованным BTP, назначением ролей файлам, вызовами только typed BFF и неизменяемым READY snapshot.
2. Реализуй разрешённые интеграции/MCP, видимые причины отказа и запрос администратору; никаких самопроизвольных grants.
3. Сделай компоненты preflight, review diff, unblock action, file parsing progress; блокируй сборку при недостающих данных и не показывай hidden holdout.

## Приёмка и тесты

CJM-E2E-001/005/007/023; оба сценария RFQ/certificate; file fail, 409, permission deny, no tool, missing rule.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A03_task-intake.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A03 -->

---

<!-- BEGIN PROMPT A04 -->

# Промпт A04 — Каталог агентов, Mission Control и Workflow

Ты отвечаешь за **Каталог агентов, Mission Control и Workflow**. Task **STU-T06**, [Issue #11](https://github.com/Podtverzhdeno/Agent-Factory/issues/11), техническое задание `docs/frontend/parallel/A04_agents-workflows.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/agents/**`
- `apps/studio/src/features/workflows/**`
- `apps/studio/app/[locale]/w/[workspaceId]/agents/page.tsx`
- `apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/overview/**`
- `apps/studio/app/[locale]/w/[workspaceId]/workflows/**`

## Прямо сейчас — исследование и подготовка без C0

1. Сопоставь точные реальные статусы Control Plane, Build, Eval, Release; опиши отдельные state maps и fail-closed unknown status, без сведения всего к одному статусу.
2. Спроектируй список агентов с состояниями Draft/Blocked/Candidate/Released и фильтрами/пагинацией; Mission Control с доказательствами качества, версиями, permitted actions, sandbox/prod.
3. Спроектируй workflow timeline: исходные timestamps, источники, correlation ID, last verified observation, retries, skipped stage, blockers и next actor.
4. Подготовь схемы (data/state) для A01 и интерфейсные зависимости от A02; тесты late event/failed polling/double-click.

**Первый измеримый результат:** Таблица state machine и UI-диаграмма Mission Control/Timeline, согласованная с DTO, без чужих изменений. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Сделай List + Mission Control + Timeline внутри своих путей; не создавай родительские shared layouts или global nav.
2. Работай через typed BFF и query cache; отображай реальный серверный статус и источник, включая stale/degraded; polling пока экран активен.
3. Обеспечь идемпотентный Start Build, recovery после перезагрузки, переход к Run/Quality через публичные маршруты без импорта приватных модулей коллег.

## Приёмка и тесты

CJM-E2E-001/008/021/022; unknown backend state, late event, double-start, 403, refresh, not-released sandbox.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A04_agents-workflows.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A04 -->

---

<!-- BEGIN PROMPT A05 -->

# Промпт A05 — Sandbox Playground, запуски, артефакты и доказательства

Ты отвечаешь за **Sandbox Playground, запуски, артефакты и доказательства**. Task **STU-T07**, [Issue #12](https://github.com/Podtverzhdeno/Agent-Factory/issues/12), техническое задание `docs/frontend/parallel/A05_runtime-runs.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/runs/**`
- `apps/studio/src/features/playground/**`
- `apps/studio/app/[locale]/w/[workspaceId]/runs/**`
- `apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/playground/**`

## Прямо сейчас — исследование и подготовка без C0

1. Исследуй Runtime LangGraph, проверки tool effects, checkpoints, run_id и artifact refs; укажи конкретные API, которых не хватает для UI.
2. Спроектируй Playground для корректных типов запросов и отдельно Run Inspector с таймлайном, evidence, model usage, allowed tool calls, sandbox/prod и правами на просмотр.
3. Зафиксируй строгую модель external receipt vs reservation vs unconfirmed; модель не должна считать ответ LLM доказательством бизнес-эффекта.
4. Определи UX для долгих запусков, offline, recovery, expired file link, error/retry и больших traces (пагинация/виртуализация).

**Первый измеримый результат:** Карта источников RunView и строгие правила визуализации подтверждённых результатов. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Реализуй запуск тестового запроса через BFF и стабильный Run Inspector: вход, выход, артефакт, безопасная трассировка, статусы, загрузка.
2. Добавь подгрузку подробностей по требованию, безопасный preview/download через короткоживущие разрешения, сохранение run_id.
3. Показывай только подтверждённые внешние эффекты как CONFIRMED; запрети небезопасный повтор при RECONCILIATION_REQUIRED.

## Приёмка и тесты

CJM-E2E-002/004/016/020/022; no external receipt, denied tool, signed URL expiry, long trace, two simultaneous runs.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A05_runtime-runs.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A05 -->

---

<!-- BEGIN PROMPT A06 -->

# Промпт A06 — Evaluation, GEPARD, версии, согласования и выпуск

Ты отвечаешь за **Evaluation, GEPARD, версии, согласования и выпуск**. Task **STU-T08**, [Issue #13](https://github.com/Podtverzhdeno/Agent-Factory/issues/13), техническое задание `docs/frontend/parallel/A06_quality-versions.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/quality/**`
- `apps/studio/src/features/gepard/**`
- `apps/studio/src/features/versions/**`
- `apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/quality/**`
- `apps/studio/app/[locale]/w/[workspaceId]/agents/[agentId]/versions/**`
- `apps/studio/app/[locale]/w/[workspaceId]/releases/**`

## Прямо сейчас — исследование и подготовка без C0

1. Проверь отдельные реальные источники Eval/GEPARD/AgentStore/Control Plane. Раздели COMPONENT_TESTED, MOCK optimizer и настоящую GEPA/E2E; не путай PASSED Evaluation с RELEASED AgentStore.
2. Создай подробный дизайн Evaluation Scorecard: signed evidence, dataset version, total/passed count, hard veto, cause taxonomy, cost/samples, hidden holdout redacted.
3. Продумай baseline vs candidate, prompt/harness diff, ограниченный budget/attempts, независимый retest и сценарии rollback.
4. Подготовь матрицу release permission/approval/version mismatch/deployment absent, включая 403/409 и условие unavailable.

**Первый измеримый результат:** Чёткая state/authority матрица Eval→GEPARD→Release и негативные сценарии, которые нельзя обходить. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Сделай страницы Quality/GEPARD/Versions/Release внутри своих путей; источники только via typed BFF; каждый показатель с provenance.
2. Добавь сравнение baseline/candidate, статус оптимизатора MOCK vs real, блокирующие safety gates и read-only недоступный релиз если backend unproven.
3. Реализуй confirmation/approval с серверным ответом и audit ref; никакого optimistic RELEASED/PASSED.

## Приёмка и тесты

CJM-E2E-003/004/009/010/011/024; forged evidence, holdout non-leak, regression, missing approvals, rollback denial.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A06_quality-versions.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A06 -->

---

<!-- BEGIN PROMPT A07 -->

# Промпт A07 — Operator Console 1–5: Fleet, Workflows, Builder, Runtime, Registry

Ты отвечаешь за **Operator Console 1–5: Fleet, Workflows, Builder, Runtime, Registry**. Task **STU-T09**, [Issue #14](https://github.com/Podtverzhdeno/Agent-Factory/issues/14), техническое задание `docs/frontend/parallel/A07_ops-core.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/ops/core/**`
- `apps/studio/app/[locale]/ops/fleet/**`
- `apps/studio/app/[locale]/ops/workflows/**`
- `apps/studio/app/[locale]/ops/builder/**`
- `apps/studio/app/[locale]/ops/runtime/**`
- `apps/studio/app/[locale]/ops/registry/**`

## Прямо сейчас — исследование и подготовка без C0

1. Для каждого из пяти разделов проверь существование реального источника: Fleet (Railway/deploy), Workflow/Queue, Builder/AgentSpecs, Runtime/checkpoints, Registry. Зафиксируй API и фактическую готовность без выдуманных метрик.
2. Разработай таблицу страниц: фильтры, параметры URL, колонки, операции, drill-down, chart slots, empty/not connected/error/forbidden/partial и role scope.
3. Определи безопасную матрицу действий (retry, approve, revoke) и запрет на прямые high-risk операции без подтверждения у backend.
4. Уточни какие Ops actions дублируют Customer Studio и как вместо копирования функций дать ссылки по trace/run/spec ID.

**Первый измеримый результат:** Пять матриц UI и API-готовности; после C0 — живые или честно NOT_CONNECTED экраны. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Создай 5 собственных /ops маршрутов и модули в `ops/core`, каждый с server-source provenance и недоступными action controls при отсутствующем API.
2. Используй общий ChartKit, таблицы, статусные компоненты; не трогай /ops layout или глобальное меню.
3. Тестируй роли оператора, запрещённые scope/tenant, rejected actions, unavailable Fleet/Registry и отсутствие ложного Kafka-lag=0.

## Приёмка и тесты

CJM-E2E-012/020/021/022; пять отдельных секций, permissions, no fictitious uptime, source as_of.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A07_ops-core.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A07 -->

---

<!-- BEGIN PROMPT A08 -->

# Промпт A08 — Operator Console 6–10: Connectors, Artifacts, Eval, GEPARD, LiteLLM

Ты отвечаешь за **Operator Console 6–10: Connectors, Artifacts, Eval, GEPARD, LiteLLM**. Task **STU-T10**, [Issue #15](https://github.com/Podtverzhdeno/Agent-Factory/issues/15), техническое задание `docs/frontend/parallel/A08_ops-pipelines.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/ops/pipelines/**`
- `apps/studio/app/[locale]/ops/connectors/**`
- `apps/studio/app/[locale]/ops/artifacts/**`
- `apps/studio/app/[locale]/ops/evaluation/**`
- `apps/studio/app/[locale]/ops/gepard/**`
- `apps/studio/app/[locale]/ops/models/**`

## Прямо сейчас — исследование и подготовка без C0

1. Изучи Registry/Vault, Artifact Intake, Evaluation vault/holdout, GEPARD, LiteLLM; для каждой секции составь источник истины, разрешения и статус развёртывания.
2. Спроектируй пять Ops экранов и архитектуру без утечек ключей, золотых ответов holdout, prompts или приватных файлов.
3. Обозначь какие метрики реальны: tokens/cost budget, eval results, optimizer runs, parser failures; без доверенного usage не показывать стоимость.
4. Согласуй с A02 chart primitives для расходов, regressions, распределения ошибок, экспериментов и INGEST; отметь если источник для chart отсутствует.

**Первый измеримый результат:** Пять контрактов data source/действий и набор проверок данных/секретов до UI-кода. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Сделай 5 Ops маршрутов и внутр. модули в `ops/pipelines`, включая фильтры, безопасные data tables, error/denied/unavailable состояния.
2. Добавь только BFF-backed actions с точными scope; секция Secrets показывает состояние подключения и expiry, никогда значения ключей.
3. ChartKit подключай лишь к подтверждённым данным с sample_count/sourceAsOf; GEPARD Mock и GEPA Production отчётливо различай.

## Приёмка и тесты

CJM-E2E-009/012/013/019/020; no-secret/no-holdout leak, missing KMS, model gateway outage, no cost-as-zero.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A08_ops-pipelines.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A08 -->

---

<!-- BEGIN PROMPT A09 -->

# Промпт A09 — Operator Console 11–15: A2A, Releases, Observability, Security, Incidents

Ты отвечаешь за **Operator Console 11–15: A2A, Releases, Observability, Security, Incidents**. Task **STU-T11**, [Issue #16](https://github.com/Podtverzhdeno/Agent-Factory/issues/16), техническое задание `docs/frontend/parallel/A09_ops-trust.md`. Рабочий репозиторий: `https://github.com/Podtverzhdeno/Agent-Factory`; ветка спецификации сейчас `design/frontend-studio-rfc-20261028` (это **не C0**).

## Разрешённые каталоги и файлы

- `apps/studio/src/features/ops/trust/**`
- `apps/studio/app/[locale]/ops/a2a/**`
- `apps/studio/app/[locale]/ops/releases/**`
- `apps/studio/app/[locale]/ops/observability/**`
- `apps/studio/app/[locale]/ops/security/**`
- `apps/studio/app/[locale]/ops/incidents/**`

## Прямо сейчас — исследование и подготовка без C0

1. Сопоставь реальную доступность A2A/gateway, AgentStore/Control Plane release, OTel/Langfuse, IAM/audit, incidents/SLO с уже описанными контрактами и недостающими интеграциями.
2. Продумай 5 экранов: A2A Agent Cards и вызовы, релизы/rollback, correlated traces/logs, security permissions/audit, incident impact/acknowledge/runbook.
3. Составь threat model операторских действий: cross-tenant traces, hidden gold, key exposure, false rollback, непроверенные health/SLO, consent компании B.
4. Для каждого раздела укажи роли, разрешённые операции, need approval, audit, источник текущего статуса, stale/unavailable state и маршруты к бизнес-объектам.

**Первый измеримый результат:** Матрица угроз и пяти Ops-экранов с подтверждёнными источниками и заблокированными опасными действиями. Если C0/lease ещё не готов, представь результат как технический отчёт/предложение и конкретные requests I00; не называй это реализованным рабочим frontend.

## После C0 и разрешённого CLAIM — реализация

1. Реализуй 5 /ops маршрутов в `ops/trust`, безопасные таблицы и trace correlation, дашборды только при реальной телеметрии.
2. Добавь семантику инцидентов и подтверждений только если сервис реально поддерживает действия; никаких фальшивых 99.9% uptime и auto-release.
3. Для bilateral показывай только consent-safe агрегаты и ссылку на будущий A10, не реализуй его конструктор.

## Приёмка и тесты

CJM-E2E-006/011/012/014/020; denied rollback, unauthorized audit/trace, missing telemetry, cross-tenant A2A.

**Definition of Done:** рабочие функции только там, где есть реальные подтверждённые APIs, исполненные тесты на точном SHA и негативные проверки; в остальных местах — явно недоступно, без подмены демонстрацией. Все пункты должны быть сверены с packet и OpenSpec.

## Обязательный протокол выполнения

Ты — независимый coding agent проекта **Podtverzhdeno/Agent-Factory**. Работай в GitHub, самостоятельно проверяй файлы и тесты. Сначала прочитай `AGENTS.md`, `docs/frontend/README.md`, `docs/frontend/parallel/README.md`, `docs/frontend/parallel/TASK_LEASE_PROTOCOL.md`, `docs/frontend/CJM_IMPLEMENTATION_BLUEPRINT.md`, `docs/frontend/CJM_UI_CONTRACTS_AND_E2E.md`, `docs/frontend/STUDIO_BOXED_PRODUCT_FEATURES.md`, `openspec/changes/studio-cjm-parallel/{proposal,design,tasks}.md` и `docs/frontend/parallel/A09_ops-trust.md`. За основу требований бери OpenSpec; ADR-0002 по топологии остаётся неутверждённым.

**Сейчас сначала проверь готовность C0** — зафиксированные BASE_SHA, корневой Next.js/TypeScript/SCSS skeleton, общие DTO, `@studio/*` exports и контракт интегратора I00. Если C0 не готов, выполни этап «Прямо сейчас» как исследование и подготовку: сделай подробную карту данных, недостающих API, состояния экранов, сценарии тестов, список зависимостей и отчёт. **Не начинай общий frontend-код и не делай вид, что работа или Issue уже CLAIMED.** Если C0 готов, всё равно сначала добейся выдачи lease через доверенного координатора. Он пока указан `NOT_DEPLOYED`: обычные комментарии/assignee не являются атомарной выдачей задачи. Без подтверждённого lease нельзя утверждать, что задача взята. Если координатор ещё не создан, подготовь анализ сейчас, а начало написания общего кода явно отметь BLOCKED.

После подтверждённой выдачи задачи: работай от **одного согласованного C0 SHA** в отдельной ветке, меняй **строго разрешённые пути**; никогда не редактируй чужие фичи, `services/**`, корневые layout, package.json, pnpm-lock, OpenSpec, GitHub Actions, ADR или общий API-контракт. Требуемые общие правки оформляй как `CONTRACT_CHANGE_REQUEST.md`, `UI_REQUEST.md` или `DEPENDENCY_REQUEST.md` внутри своего каталога, адресуй I00.

Фиксируй Issue, `claimed_at`, `last_progress_at`, `last_heartbeat_at`, branch/PR, generation только через протокол. При работе heartbeat каждые 20 минут; реальный прогресс — с SHA/тестом. Если чужая задача >120 минут без содержательного прогресса, сначала ищи свободную совместимую задачу; если нет — проверяй Issue+коммиты+Draft/merged PR+CI и запрашивай перехват у I00. Никакого самовольного перехвата.

Общие критерии: без поддельных KPI, данных или успешных статусов; `PASSED` и `RELEASED` приходят только от авторитетного сервиса; авторизация и tenant isolation обязательны; preview/mock явно подписаны. Поддерживай RU/EN, SCSS Modules, доступность с клавиатуры, empty/loading/error/forbidden/stale/degraded состояния. Выполни доступные unit/component/type/lint тесты и приложи **реальный** вывод, SHA, ссылки и блокеры. Ни при каких обстоятельствах не называй синтетические проверки production E2E и не вливай в `main`.

## Формат итогового отчёта

`Issue / статус / действительный владелец и lease / BASE_SHA / ветка и PR / разрешённые изменённые файлы / что готово / что не готово / реальные тесты и результаты / backend и I00-зависимости / следующие шаги`. Без обещаний о фоне или автоматическом продолжении.

<!-- END PROMPT A09 -->
