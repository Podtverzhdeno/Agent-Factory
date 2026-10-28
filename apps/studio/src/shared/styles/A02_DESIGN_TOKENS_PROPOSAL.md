# A02 semantic tokens, density, themes and SCSS Modules proposal

**Status:** design-only; no global CSS imported, no app skeleton, no tests run. I00 must freeze C0 and approve root import. **Owner boundary:** A02 shared/styles only; I00 owns root layout and all package/SCSS toolchain config.

## Token strategy

- One centrally imported CSS custom-property source; SCSS Modules only for component-local selectors and small mixins. CSS variables are runtime-themeable and exposed through the contract; no random per-feature palettes.
- Semantic names, not raw color names: --studio-fg, --studio-fg-muted, --studio-surface, --studio-surface-raised, --studio-canvas, --studio-border, --studio-border-strong, --studio-focus, --studio-action, --studio-action-fg, --studio-success, --studio-warning, --studio-danger, --studio-chart-1..8, --studio-shadow-elevation-1/2.
- Theme selection via I00-owned root attribute: data-theme="light" | "dark", with explicit system fallback. A02 files define theme values; I00 wires persistence and imports.
- Data-derived statuses always carry **text + icon/pattern**. No hue can by itself mean "verified", "released", "failed" or "blocked".

## Proposed starting tokens (to be checked for contrast on real elements)

| Semantic token | Light | Dark | Usage |
| --- | --- | --- | --- |
| canvas | #F8FAFC | #0B1220 | page background |
| surface | #FFFFFF | #111C30 | cards/dialogs |
| surface-raised | #F1F5F9 | #1B2A42 | hover/selected |
| foreground | #0F172A | #F8FAFC | primary text |
| foreground-muted | #475569 | #CBD5E1 | supporting labels |
| border | #CBD5E1 | #475569 | separators |
| action | #1D4ED8 | #93C5FD | controls/links |
| action-foreground | #FFFFFF | #0B1220 | CTA text |
| positive | #166534 | #86EFAC | source-confirmed positive only |
| warning | #92400E | #FCD34D | partial/degraded/stale |
| danger | #991B1B | #FCA5A5 | errors/destructive actions |
| focus | #1D4ED8 | #93C5FD | visible focus ring |

**Not a branding approval:** all colors are provisional; I00/product design owns brand decision. Verify WCAG 2.2 AA normal text contrast 4.5:1, large text ≥3:1, interactive boundaries/focus ≥3:1 and High Contrast/forced-colors. Check disabled/read-only states without relying on lowering opacity to illegibility.

## Typography, density and layout

- Font stack proposal: system-ui, -apple-system, "Segoe UI", sans-serif; no external font request until design owner approves licensing/asset budget.
- Typographic scale: body 14–16px, compact data-cell ≥13px, titles 18/24/30px; line-height 1.4–1.6 and tabular-nums for aligned counters; do not truncate evidence strings without accessible expansion.
- Spacing: 4px base; proposed --studio-space-1=4px, -2=8, -3=12, -4=16, -5=20, -6=24, -8=32, -10=40, -12=48.
- Radii: 6px small, 10px medium, 14px large, pill 9999px. Controls ≥40px tap targets; compact desktop may use 36px only where accessibility exceptions are justified and tested.
- Density modes: comfortable by default; compact can reduce table padding but not keyboard/touch target availability.
- Breakpoint checks: 360/390 mobile, 768 tablet, 1024 desktop, 1440 wide. Use container-based adjustments where supported, avoid root CSS overrides.
- Long RU/EN translation, ISO dates, UUIDs and reason codes must wrap gracefully; RTL not required by current RU/EN scope, but components should not rely on left-only spacing.

## Motion and interaction

- Motion durations: 120–180ms focus/hover, 180–240ms dialog enter, <=250ms page transitions; no layout-shifting celebratory animation for status changes.
- prefers-reduced-motion: reduce → disable nonessential animation/transforms, avoid scroll animation, retain visible focus and deterministic UI.
- Focus: outline ≥2px with visible offset; focus trap/restore for modal, roving focus for tabs, keyboard-visible tooltip.
- Loading: aria-busy on relevant region, delayed skeleton only for actual pending requests; never visually equate "loading" with "successful execution".
- Source statuses: COMPLETE uses normal content, PARTIAL attaches denominator disclosure, STALE timestamp and degraded warning, UNAVAILABLE explains source, UNSUPPORTED gives version/reason.

## Proposed file layout after authorized C0

~~~text
apps/studio/src/shared/styles/
  tokens.css          # CSS variables, themes; I00 imports once
  _mixins.scss        # focus, screen-reader-only, responsive helpers
  _density.scss       # component-local utility mixins
apps/studio/src/shared/ui/
  Button/Button.tsx
  Button/Button.module.scss
  ...                 # colocated component tests
~~~

No production file above exists yet because C0 and task lease are absent.

## Integration requests to I00

- Confirm theme root attribute and locale bridge; approve any brand color changes and root token import.
- Define SCSS compiler support in global package; local A02 must not edit package.json, lockfiles or Next config.
- Add real dual-theme contrast, keyboard and reduced-motion CI gates on the integrated C0 branch; A02 provides component evidence after claim.
- Define component responsive screenshot infrastructure and non-color status cues; no screenshot or contrast test is being claimed now.
