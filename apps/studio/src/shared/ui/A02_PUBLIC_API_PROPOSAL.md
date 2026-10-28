# A02 pre-C0 shared UI public API proposal

**Status:** DESIGN ONLY, not compiled or deployed. **Task:** STU-T04 / issue #9; no granted lease. **Base:** documentation branch design/frontend-studio-rfc-20261028, NOT the integrator C0 SHA.
**Scope:** AF-REQ-123, plus shared accessibility/state needs in AF-REQ-114/115. The code sketch below is a proposal; exact exports and aliases are owned/frozen by I00.

## 1. Shared interface principles

- All primitives are **presentation-only**. Authorization, tenant scoping, source status, grants, file access, command idempotency and confirmation are server-owned.
- No component accepts a naked flag that can convert an unauthorized operation to an authorized one. An action's visible state is derived from the BFF ActionDescriptor; the BFF/service revalidates on click.
- UI consumes message keys + interpolation parameters, not hardcoded Russian-only strings. I00 owns the RU/EN dictionary provider and default locale contract. English identifiers, user copy in RU and EN.
- Use native semantics first (button/input/table/dialog where supported); don't assign role=button to generic div. Never hide essential actions behind hover alone.
- Unknown state/unknown enum → fail closed, visibly unsupported with a source reason. Never infer VERIFIED or RELEASED from optimistic UI.

## 2. Proposed TypeScript public surface (NOT source code)

~~~ts
type UiLocale = "ru" | "en";
type MessageKey = string; // I00 decides typed key registry at C0
type UiSize = "sm" | "md" | "lg";
type UiTone = "neutral" | "brand" | "success" | "warning" | "danger";

interface SourceLabel {
  source: string;
  sourceAsOf: string | null;        // RFC3339 UTC, null means unknown
  completeness: "COMPLETE" | "PARTIAL" | "UNAVAILABLE" | "STALE" | "UNSUPPORTED";
  revision: string | null;
  sampleCount?: number | null;
  reasonCode?: string | null;
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: UiSize;
  loading?: boolean;
  iconOnlyLabelKey?: MessageKey;
  // Disabled reason is rendered in nearby descriptive text, not tooltip alone
  disabledReasonKey?: MessageKey | null;
}
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  labelKey: MessageKey;
  hintKey?: MessageKey;
  errorKey?: MessageKey;
  requiredIndicator?: boolean;
}
interface FormFieldProps {
  name: string; labelKey: MessageKey; hintKey?: MessageKey;
  errorKey?: MessageKey; required?: boolean; children: React.ReactNode;
}
interface DialogProps {
  open: boolean;
  titleKey: MessageKey;
  descriptionKey?: MessageKey;
  onOpenChange(open: boolean): void;
  children: React.ReactNode;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
}
interface TabsItem { id: string; labelKey: MessageKey; disabled?: boolean; reasonKey?: MessageKey }
interface TabsProps { items: readonly TabsItem[]; activeId: string; onChange(id: string): void; labelKey: MessageKey; }

interface TableColumn<Row> {
  id: string; headingKey: MessageKey;
  getCell(row: Row): React.ReactNode;
  sortKey?: string; // server-side whitelist, not untrusted field name
}
interface DataTableProps<Row> {
  captionKey: MessageKey;
  columns: readonly TableColumn<Row>[];
  rows: readonly Row[];
  getRowId(row: Row): string;
  nextCursor: string | null;
  onPageRequest?: (cursor: string) => void;
  sort?: { key: string; direction: "asc" | "desc" } | null;
  onSortChange?: (key: string, direction: "asc" | "desc") => void;
  loading?: boolean;
}

type PageState =
  | { kind: "loading"; messageKey?: MessageKey }
  | { kind: "empty"; messageKey: MessageKey; source?: SourceLabel }
  | { kind: "ready"; source: SourceLabel }
  | { kind: "partial"; source: SourceLabel; warningKey: MessageKey }
  | { kind: "stale"; source: SourceLabel; warningKey: MessageKey }
  | { kind: "unavailable" | "degraded" | "error"; messageKey: MessageKey; reasonCode?: string; source?: SourceLabel }
  | { kind: "forbidden"; messageKey: MessageKey };
interface PageStateProps { state: PageState; children?: React.ReactNode; retry?: () => void; }

interface StatusBadgeProps { state: string; labelKey: MessageKey; tone: UiTone; reasonCode?: string; }
interface TimelineEntry {
  id: string; labelKey: MessageKey; occurredAt: string | null;
  source: SourceLabel; state: string; detailKey?: MessageKey;
}
interface TimelineProps { entries: readonly TimelineEntry[]; labelKey: MessageKey; }
interface UploadUiFile {
  id: string; name: string; sizeBytes: number;
  state: "selected" | "uploading" | "processing" | "accepted" | "rejected" | "failed";
  progressPercent?: number; reasonCode?: string;
}
interface FileUploadUiProps {
  files: readonly UploadUiFile[];
  acceptHintKey: MessageKey;
  onSelect(files: FileList): void; // caller owns signed upload, checksums and rights
  onRetry?(fileId: string): void;
  disabled?: boolean;
  disabledReasonKey?: MessageKey;
}
interface SafeTooltipProps { contentKey: MessageKey; children: React.ReactElement; }
interface PageShellSlotProps { headingKey: MessageKey; actions?: React.ReactNode; children: React.ReactNode; }
interface SourceProvenanceProps { source: SourceLabel; redacted?: boolean; }
~~~

**Requested entrypoints:** @studio/ui → Button, Input, FormField, Dialog, Tabs, DataTable, StatusBadge, Timeline, FileUploadUi, PageState, Card, Alert/Callout, SafeTooltip, SourceProvenance, PageShellSlot. @studio/charts → ChartView only. No direct imports of other workstreams' internals.

## 3. Behavior / edge-state matrix

| Primitive | Accessibility and interaction | Failure / source handling |
| --- | --- | --- |
| Button | native button, disabled while pending; icon-only has accessible name | forbidden action shows reason outside hidden tooltip, no client-side fake authorization |
| Input / FormField | label/id association, aria-describedby for help/error, invalid announced once | retain unsaved values on 409; server errors mapped to safe message keys |
| Dialog | modal focus entry/contain/return, Escape unless action is explicitly non-dismissable | never treat closing dialog as a completed domain command |
| DataTable | caption, real thead/th, logical scope, keyboard pagination/sort | null ≠ zero; server paging only; CSV handled by authorized BFF |
| StatusBadge | icon/text + color, unknown enum shows explicit unsupported | no green for unverified status |
| Timeline | ordered timestamps, source/timezone labels, accessible textual list | out-of-order or missing steps remain source-reported, no inferred completion |
| Tabs | roving focus, arrow/home/end keys, active aria-selected | preserve focus and route state on change |
| FileUpload UI | drag/drop plus keyboard-select input; live status and retry buttons | no direct credential handling; reject unknown MIME and denied rights at backend |
| PageState | distinct loading/empty/partial/stale/error/unavailable/forbidden | status keeps sourceAsOf; never silently show cached stale series as current |
| SafeTooltip | click/focus-accessible, escape-dismissable, avoids HTML injection | never sole source of critical explanation |
| ChartView | described in shared/charts proposal, table/summary always available | no render if provenance and trusted count absent |

## 4. Requests to I00

1. Freeze shared SourceStamp, SafeError and ActionDescriptor exports and strongly typed localization key provider. Provisional local UI types are **not** final DTOs.
2. Publish @studio/ui and @studio/charts aliases and stable package barrel interface in C0.
3. Import root CSS custom-properties from A02 shared/styles after review. A02 will not touch root layouts or global providers.
4. Define exact auth and error boundaries for 401/403/409/429/503. Display reasons but do not expose other-tenant record existence.
5. Confirm whether PageShellSlot belongs to A02 as a compositional primitive (route shell/global layout remains I00-owned).

## 5. Acceptance plan (not executed)

- Keyboard focus and escape/return: Dialog, Tabs, Tooltip, FileUpload.
- All controls: light/dark, disabled, busy, error, empty, reduced-motion, RU/EN text expansion, 360/390/768/1440px.
- axe-core/WCAG 2.2 AA target; measure contrast and inspect screen reader speech manually, not just screenshots.
- SourceState unknown, 403, disconnected source, 429 retry-after, 503 and stale projection do not trigger privileged commands.
- Only after C0+lease: local component tests/strict TS/SCSS/lint on exact SHA; I00 owns final integration E2E and release judgments.
