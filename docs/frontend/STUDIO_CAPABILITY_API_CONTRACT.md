# Studio BFF — feature availability / boxed product status read contract

**PROPOSED ONLY.** This is a boundary contract for future implementation, not a deployed or authorized endpoint. ADR-0002 still awaits owner ratification.

## Why two sources, not one?

The static checked-in `STUDIO_FEATURE_CATALOG.json` is **what we intend to ship** (product commitment, phase, owner, route). It MUST NEVER be used to determine whether the feature currently works or whether a user can invoke it.

The authenticated BFF dynamically computes a safe **effective availability projection**, using actual service deployment identity, versioned API readiness, source quality evidence, environment, workspace subscription if relevant, user role/scopes, approvals and current source health. A static feature catalog may define IDs/descriptions but must not mint permissions or green status.

## Proposed read API

`GET /api/studio/capabilities?workspace_id={authorized-workspace}`

- Authenticate user using secure server-side session, resolve tenant and environment from trusted session; any requested workspace ID must be authorized.
- Return only permitted feature descriptions; operator-only confidential metadata is excluded for business users.
- `Cache-Control: private, no-store` for permissions and tenant-dependent values, `Vary` or explicit no shared caching.
- Issue a server `as_of`, `projection_revision` and schema version. On a permission or source change, invalidate connected UI caches.
- Source adapters have bounded timeouts; unknown/unavailable backend state is NOT a positive status.

### Public DTO example (illustrative, no live implementation)

~~~json
{
  "schema_version": "studio.capabilities.v1",
  "workspace_ref": "authorized-workspace",
  "environment": "SANDBOX",
  "as_of": "2026-10-28T08:00:00Z",
  "projection_revision": "rev-illustrative",
  "features": [
    {
      "id": "studio.bilateral",
      "box_scope": "ADVANCED_COMMITTED",
      "delivery_phase": "AFTER_BILATERAL_E2E",
      "evidence_level": "DESIGN_ONLY",
      "availability": "PLANNED",
      "reason_code": "BILATERAL_E2E_NOT_PROVEN",
      "allowed_actions": []
    },
    {
      "id": "studio.langgraph_visual_editor",
      "box_scope": "IDEA_ONLY",
      "delivery_phase": "NO_IMPLEMENTATION",
      "evidence_level": "DESIGN_ONLY",
      "availability": "ROADMAP_IDEA",
      "reason_code": "NOT_IMPLEMENTED",
      "allowed_actions": []
    }
  ]
}
~~~

### Fields and invariants

| Field | Values/meaning | Rule |
| --- | --- | --- |
| `id` | stable product capability ID | Must match catalog or be safely unknown |
| `box_scope` | CORE_REQUIRED / OPERATOR_REQUIRED / ADVANCED_COMMITTED / IDEA_ONLY | Product commitment, **not** technical readiness |
| `delivery_phase` | first pilot / staged / later / idea | Planning only |
| `evidence_level` | DESIGN_ONLY / CODE_PRESENT / COMPONENT_TESTED / SYNTHETIC_INTEGRATION_TESTED / REAL_STAGING_TESTED / PRODUCTION_VERIFIED | A source SHA/verification link is required to claim beyond CODE_PRESENT; no auto-upgrading |
| `availability` | ROADMAP_IDEA / PLANNED / DISABLED / PREVIEW / AVAILABLE / DEGRADED / FORBIDDEN | Server-computed actor, env, entitlement, health and gates; unknown → DISABLED |
| `reason_code` | stable safe machine code | Never expose secrets/tenant existence through denial |
| `allowed_actions` | exact permitted action IDs | Server re-check on every mutation; list is UX hint, not authorization |
| `source_as_of` | timestamp of last trusted data | stale must not be rendered current |
| `source_completeness` | optional verified completeness for telemetry | incomplete ≠ zero |
| `evidence_ref` | operator-only trusted verification ref | default hidden for customers |

**A planned page may be visible as Roadmap or to authorized operator reviewers even when not active.** Customer active navigation should not contain clickable non-working links masquerading as available. Show “Планируется”/“Недоступно: нет подтверждённой интеграции” with a design-preview label, rather than empty functional screens.

### Explicit unlock rule

`AVAILABLE` only when every one of:
1. feature is implemented, deployed in requested environment and compatible with required service/API revisions;
2. any required security/integration/E2E gates have independent, immutable evidence;
3. actor, tenant and role are authorized to see data and perform **each** requested action;
4. all blocking upstream dependencies are healthy or have safe degraded operation;
5. protected dataset or external business effect rules are actually enforced.

For the **two-company builder**, additionally both parties' consent, per-tenant isolation, real A2A client/server execution, signed A/B/joint Evaluation, separate approvals and cross-play regression are mandatory. For **Release**, a passing mock or signed synthetic Quality test is insufficient without production attested release + deployment result.

For the **visual LangGraph editor and microfrontends**, these are IDEA_ONLY and cannot be unlocked by an operator feature flag; future approved implementation must add real endpoints and tests first.

### Charts

The chart library is mandatory product scope but **individual charts are capability-backed data products**: `chart_id` + source + timeframe + units + sample_count + `source_as_of` + completeness. No dataset → show "Нет подтверждённых данных"; never synthesize plot points. Operator can inspect source evidence; public user receives authorized aggregation only.

## BFF/TypeScript example (illustrative, not shipped)

~~~ts
type Availability =
  | "ROADMAP_IDEA"
  | "PLANNED"
  | "DISABLED"
  | "PREVIEW"
  | "AVAILABLE"
  | "DEGRADED"
  | "FORBIDDEN";

interface FeatureProjection {
  id: string;
  availability: Availability;
  reason_code?: string;
  allowed_actions: readonly string[];
}

function canOfferAction(
  feature: FeatureProjection,
  actionId: string,
): boolean {
  return feature.availability === "AVAILABLE"
      && feature.allowed_actions.includes(actionId);
}
~~~

**Important:** `canOfferAction` is presentation logic only. BFF and owner service MUST enforce authorization and release policy again on every command; do not regard browser UI state as a security gate.

## Testing requirements

- Role revoked after page load: BFF rejects mutation, SSE/poll refresh updates UI state.
- Source API reports 500 or unknown enum: BFF flags unavailable/degraded, never returns success.
- Other tenant uses deep link, shared CDN cache or workspace switch: no disclosure of existence/data/feature entitlements.
- Editor and MFE ideas remain roadmap-only and cannot be enabled by any feature toggle.
- Bilateral preview with only A's approval refuses to run.
- Operator charts with no real source display unavailable, not dummy timeseries.
- Catalog IDs unknown to frontend safely ignore/label; API source version mismatch fail closed for privileged actions.

**No user-facing dashboard or service feature availability is established by this document alone.**