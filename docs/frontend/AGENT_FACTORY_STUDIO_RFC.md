# RFC — Agent Factory Studio: клиентский портал и операционная консоль

**Дата:** 2026-10-28  
**MVP implementation cutline:** [`STUDIO_MVP_SCOPE_DECISION.md`](STUDIO_MVP_SCOPE_DECISION.md) supersedes the feature priorities in this aspirational RFC. Build the real business vertical slice before introducing additional screens and infrastructure.  
**Статус:** PROPOSED / UX + contract-first, без авторизации архитектуры или заявлений о готовом UI.  
**Базовая спецификация:** `docs/product/MVP.md`, `docs/architecture/BUSINESS_TASK_PACKAGE_RFC.md`, `docs/parallel/CONTRACTS_V0.md`.  
**Зависимости:** ADR-0002 (владельцу необходимо утвердить сервисные границы), реальные Task Intake и artifact APIs, интеграционные и операционные контракты.

## 1. Принцип продукта

Клиент покупает и управляет **проверенным исполнением бизнес-операции**, а не конструктором узлов. Основной P0 — один специализированный агент для одной бизнес-задачи. Совместный A2A-сценарий двух компаний — опция, не блокирует MVP.

Два представления поверх одной серверной модели:
- **Business Workspace:** задача → файлы/правила → разрешения → критерии → создать → испытать → согласовать → использовать → результат и расходы.
- **Operator Console:** очереди, версии и манифесты, технические шаги, трассы, правила доступа, ревизии, расследование инцидентов, аудиты, SLA и откат.
- Представления отличаются **данными и разрешёнными действиями**, а не просто CSS и скрытыми кнопками. Бэкенд повторно проверяет авторизацию каждой операции.

Не предлагать человеку собрать LangGraph как обязательное условие. Технический граф — вторичный режим эксперта; основной интерфейс — guided task creation.

## 2. Навигация и роль

Общая навигация: **Обзор / Агенты / Запуски / Интеграции / Качество / Рабочее пространство**. Кнопка **«Создать агента»** заметна всегда в контексте соответствующих прав.

Внутренние дополнительные разделы: **Задачи и очереди / Tool & MCP Registry / Операционный аудит / Инциденты / Выпуски и откаты / Инфраструктура**.

Предлагаемые роли: Workspace Owner, Business Expert, Agent Operator, Integration Admin, Auditor (read-only), Platform Operator. Не смешивать platform-admin и customer-admin. Разрешения на операции должны быть явными и tenant-scoped.

## 3. Экраны P0

### A. Обзор рабочего пространства

- Количество агентов по проверенным состояниям, требуемые решения и последние операции.
- **Нужны действия:** отсутствие прав каталога, непроверенный шаблон, провал регрессии, истёкший токен, ожидаемое одобрение.
- KPI с источниками и периодом: количество **успешных подтверждённых** операций, стоимость/успех, latency p95, блокировки и безопасные остановки, экономия времени **только если есть валидный baseline**.
- Последние активности с ссылкой на run/agent/version; пустые и error-состояния. Нельзя отображать вымышленные значения для неподключённого API.

### B. Создать агента — мастер из пяти шагов

1. **Бизнес-задача:** формулировка человеческим языком, владелец, роль, желаемый артефакт/действие, типовые и исключительные случаи.
2. **Данные и примеры:** файлы XLSX/DOCX/PDF/CSV/OpenAPI, назначение каждого, происхождение и права, примеры «вход → ожидаемый выход»; индикаторы INGESTING/REJECTED/NEEDS_REVIEW. Защищённые holdout-файлы не должны быть доступны Builder и GEPARD.
3. **Системы и разрешения:** предложенные ERP/CRM/API/MCP инструменты, причина выбора, read vs draft vs irreversible; подключение полномочий через vault/consent, без вывода токенов в браузер.
4. **Критерии и ограничения:** факты, обязательные поля, допустимые ошибки, запрещённые действия, бюджет, задержка, сроки, approval points; обязательный владелец бизнес-правил.
5. **Сверка и запуск:** пользователю показывается нормализованный Business Task Package, недостающие ответы, границы прав, предварительные ограничения. CTA «Проверить готовность» → READY → **явная команда сборки**. Если не READY, показать точную причину и кнопку её устранения.

Помощник задаёт уточняющие вопросы по документам, но ответы становятся правилами только после подтверждения владельцем. Черновик сохраняется и имеет ревизию; READY создаёт неизменяемый snapshot.

### C. Карточка агента

Header: название, владелец, бизнес-цель, среда SANDBOX / PROD, состояние candidate/verified/released, активная версия и две CTA: **«Пробный запуск»**, **«Запросить выпуск»** (только если право и gate это позволяют).

Вкладки:
- **Обзор:** описание результата, возможности и запрещённые операции, версия, последние 5 запусков, необходимые действия.
- **Запуски:** отдельная история каждого run с фильтрами и доказательствами.
- **Качество:** scorecard, версии, регрессии, блокировки, изменения и стоимость оптимизации.
- **Архитектура:** read-only граф шагов, tool pins, MCP/A2A Card, права и точки эскалации.
- **Версии:** immutable versions, diff prompt/harness/model/tool pins, evidence/approvals, Rollback.
- **Настройки:** расписания, допустимые потребители, лимиты, данные/retention, маршруты оповещений.

### D. Страница сборки — не «вечный spinner»

Не отображать фиктивные проценты. Показывать **реальную серверную state machine** в человеческих группах:
- «Подготовка» (DRAFT, INGESTING, REQUIRES_CLARIFICATION, READY);
- «Создание» (BUILDING);
- «Проверка» (TESTING, OPTIMIZING, RE_TESTING);
- «Решение о выпуске» (VERIFIED, RELEASED, BLOCKED, ROLLED_BACK).

Для каждого шага: время, сервис-источник, сжатое описание результата, доказательства (refs), стоимость, разрешённое действие и видимость ошибки. Отображать `correlation_id` и `operation_id` только для роли оператора. Показать точный `required_action`: «Предоставьте доступ на чтение каталога», «Утвердите выходной шаблон», «Нужна ручная оценка».

### E. Выполнение отдельного run

Вверху: бизнес-результат (файл/структура/действие), статус и проверяемость внешнего эффекта. Под ним: хронология шагов «Получено → Прочитано → Проверены правила → Вызван инструмент → Подготовлен файл → Выполнена проверка». Каждый шаг раскрывается в оригинальные безопасно редактированные input/output, errors, duration, tokens, cost, model route, pinned tool manifest and trace/span reference.

**Не считать ответ модели "всё выполнено" доказательством бизнес-действия.** `effect_key`/idempotency reservation != внешняя ERP-квитанция. Для обязательного business effect нет независимого receipt → не PASS.

### F. Качество и GEPARD

Сравнение `baseline` и `candidate`: успешные сценарии, hard safety veto, required effects, p95 latency, стоимость на успешную операцию, изменение model route, diff промпта и причин. Tuning/validation доступны optimizer, sealed holdout остаётся Evaluation-only. Предложения GEPARD видны как **кандидаты**, не перезаписывают released версию. Отдельные кнопки «Повторно испытать» и «Запросить выпуск». Опасные изменения и выпуск требуют подтверждений, заданных серверной политикой.

## 4. P1 / P2

P1: двусторонний A2A-view (агент клиента ↔ агент партнёра) с согласованными, защищёнными доказательствами, чат-подобная история вызовов; comparison benchmark для LiteLLM; расширенный визуальный граф (read-only + diagnose).

P2: полноценный node editor, marketplace MCP/skills, сценарии нескольких агентов и приватное развертывание. Не превращать MVP в прямую копию n8n — графовый редактор не должен задерживать первые B2B-пилоты.

## 5. Технологическая архитектура frontend (предложение)

- `apps/studio-web`: TypeScript, React, Next.js App Router, адаптивный UI.
- `apps/studio-bff` или Next.js server route handlers: единственный public-facing BFF для UI, серверные OIDC-сессии, tenant-auth, aggregation, DTO/redaction, idempotency, rate limits; выбор отдельного BFF vs framework routes после ADR-0002.
- `packages/ui`: design tokens, базовые компоненты, accessibility, таблицы, статусы, сплит-панели; **SCSS Modules + CSS Custom Properties** как единый стиль для масштабируемого frontend.
- `packages/contracts`: OpenAPI-generated types, Zod schemas/runtime validation, typed API client, version negotiation; TypeScript strict, noUncheckedIndexedAccess, package boundaries и pinned schema revisions.
- `features/task-intake`, `agent-build`, `execution`, `quality`, `registry`, `releases`, `observability`: модульная организация без циклических импортов.
- Для real-time: **BFF SSE** с повторным подключением и `Last-Event-ID`; сервер должен возвращать tenant-validated event projections, а не сырые Kafka, DB или audit signer envelopes. Polling fallback 5–10s. Состояние после реконнекта перечитывается через GET (источник истины — сервер).
- React Flow допустим **только для inspector/операторской схемы**, не как базовый интерфейс создания агента.
- Пользователь никогда не получает provider API key, MCP secret, private Ed25519 key, holdout answer или raw cross-tenant payload. Срок жизни signed artifact URLs краткий, access rights перепроверяются на сервере.

## 6. Необходимые backend-контракты

Уже **предложены**, но не должны описываться как работающие клиентские API:
- Control Plane: `POST /v1/workflows`, `GET /v1/workflows/{workflowId}`, `GET /v1/workflows/{workflowId}/audit`, выпуск и откат — в текущем Java OpenAPI draft.
- Task Intake: `POST/PUT /v1/business-tasks`, attachments, `validate`, `ready` — пока RFC.
- Runtime / Evaluation — внутренние сервисные контракты, не прямые браузерные endpoints.

**Нужно утвердить и реализовать BFF API (новое предложение):**

| Endpoint | Назначение |
| --- | --- |
| `GET /api/studio/me` | Session, tenant workspace, scopes and granted capabilities |
| `GET /api/studio/overview` | Redacted summary + action queue; metrics with time-window and provenance |
| `GET/POST /api/studio/tasks` | Business Task Package drafts + paging |
| `GET/PATCH /api/studio/tasks/{id}` | Tenant-scoped draft, optimistic revision conflict |
| `POST /api/studio/tasks/{id}/uploads` | Authorized short-lived upload to artifact store |
| `POST /api/studio/tasks/{id}/validate` | Typed missing requirements/permission prompts |
| `POST /api/studio/tasks/{id}/ready` | Immutable snapshot & ownership verification |
| `POST /api/studio/tasks/{id}/builds` | Explicit, idempotent orchestrator command |
| `GET /api/studio/agents/{id}` | Agent card, version, state, active release |
| `GET /api/studio/agents/{id}/runs` | Paginated run history, filters |
| `GET /api/studio/runs/{id}` | Redacted run evidence + artifact refs |
| `GET /api/studio/agents/{id}/quality` | Baseline/candidate metrics and evidence availability |
| `GET /api/studio/workflows/{id}/events` | Authorized SSE with replay cursor and typed events |
| `POST /api/studio/agents/{id}/releases` | Approval-gated mutation; no bypass of server policy |
| `POST /api/studio/agents/{id}/rollbacks` | Permissioned, idempotent rollback request |

Data responses contain `status`, `status_reason_code`, `required_action`, `occurred_at`, `version`, `correlation_ref`, evidence availability flags, redaction levels. Do **not** expose confidential raw traces or secret-derived grants in client payloads.

## 7. Events and consistency

Each UI event has `event_id, schema_version, tenant_id` (the BFF validates it, but need not expose raw tenant_id), `entity_id, phase, status, occurred_at, sequence/cursor, correlation_ref, safe_summary`. Clients deduplicate events. Out-of-order events cause a fresh authoritative GET rather than visual rollback.

Never infer progress percentages by elapsed time. Never emit VERIFIED/RELEASED from model prose, browser state or a green test badge; the release state comes exclusively from Control Plane/AgentStore.

## 8. Design system

- Enterprise-grade visual identity: quiet light/dark mode, readable typography, generous whitespace, clear hierarchy; restrained deep-blue/graphite with cyan primary accent. Green for verified completion, amber for needs-action and red for hard veto. Status always has text and icon, not color alone.
- Semantic skeleton/loading; empty/error/no-permission states; persistent action buttons; accessible keyboard navigation, focus, ARIA live region for workflow updates.
- Desktop-first responsive; tablet usable; mobile supports overview/alerts/approvals but complex trace diagrams may remain desktop-focused.
- RU/EN localization, tenant-specific timezone/currency, safe display of amounts and sensitive data.

## 9. MVP delivery plan and acceptance

**Phase A — UX + contracts**: clickable five-screen prototype; user interviews with a business owner, operator and integration owner; approve page structure and BTP fields. No fake success statuses.

**Phase B — read-only live UI**: signed login, tenant isolation, agents list/detail, workflow timeline via `/v1/workflows` and `/audit`, redacted run list, error reconciliation. Requires actual backend endpoints (not just OpenAPI definitions).

**Phase C — guided creation**: Task Intake service / file upload & parsing, clarification loop, immutable snapshot, explicit build, connector consent, quality visualization.

**Phase D — operations**: authorized release, rollback, incident alerts, baseline comparisons, per-run costs, customer dashboard and operator detail.

**Gate before pilot**: 100% required tenant/RBAC negative cases, no secret or holdout exfiltration, real action → job/event updates across refresh, no fabricated status, graceful SSE replay/polling fallback, signed artifact access, accessible tab flow, full UI E2E on pinned API revision.

## 10. UX anti-patterns

- No free-form production MCP installation with inherited administrator rights.
- No obligation to manually wire a graph for an ordinary business customer.
- No unbounded "agent is thinking" spinner or invented progress percentages.
- No optimistic promotion into RELEASED.
- No exposing technical trace secrets to unprivileged customer role.
- No placeholder data masquerading as real customer KPIs.
- No shared customer/operator actions that bypass the server's role and policy checks.

**Масштабирование frontend:** обязательный сопровождающий документ: [`STUDIO_SCALABILITY_ENGINEERING.md`](STUDIO_SCALABILITY_ENGINEERING.md). Он фиксирует TypeScript strict, SCSS Modules, CSS-токены, pnpm/Turborepo, независимые feature modules, схемы BFF/SSE, тесты безопасности и критерии декомпозиции.

**Вопрос для owner ADR:** является ли Studio BFF отдельным сервисом или управляемым frontend gateway? Кто владеет Task Intake and artifact storage? До ответа проектирование логических API не утверждает физическую сервисную карту.
