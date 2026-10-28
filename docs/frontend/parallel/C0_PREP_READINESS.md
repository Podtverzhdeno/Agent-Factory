# I00 technical C0 audit — 2026-10-28

**Verdict:** **C0-R / reproducible UI foundation VERIFIED**, but **C0-READY FOR PARALLEL LIVE CLAIMS = BLOCKED**. These are separate acceptance levels. Do not infer real user services or task ownership from a green build.

## Executed acceptance evidence

- GitHub C0 commit **`08cca03a587104f2018166a46158b1c857842cdd`**: [Studio C0 reproducibility run #40677832820](https://github.com/Podtverzhdeno/Agent-Factory/actions/runs/40677832820) **SUCCESS**, [SDD run #40677832811](https://github.com/Podtverzhdeno/Agent-Factory/actions/runs/40677832811) **SUCCESS**.
- Reproducible `npm ci --ignore-scripts --no-audit --no-fund` using committed `apps/studio/package-lock.json`.
- `npm audit --omit=dev --audit-level=high` SUCCESS (production dependency audit at this SHA; not a permanent guarantee).
- `npm run typecheck` SUCCESS; `npm run lint` SUCCESS; `npm run build` SUCCESS (Next.js 16.4.3).
- `python -m unittest discover -s tests/studio-coordination -v`: **33 tests passed**, including issue actor/claim generation and stale logic, fake GitHub PR/CI reconciliation and PR file-scope/old-generation denial.
- Fail-closed protected route parents, 15 Operator navigation IDs, shared View DTOs and resolved 15 ChartKind types compiled. **No real Task Intake, auth or BFF endpoints are enabled.**

## Remaining gates — no false approval

| Gate | State | Required to unlock |
| --- | --- | --- |
| TypeScript/build/lint + lock | **VERIFIED TECHNICAL BASELINE** | Re-run on final integration SHA with same lock |
| Production npm audit | **PASSED at reviewed SHA** | Re-run per PR/dependency update |
| 15 chart taxonomy | **TYPE CONTRACT APPROVED as proposed UI** | A02 actual components, runtime schemas and source-backed data |
| Task/Run/Eval/View types | **TYPE CONTRACT PREPARED** | A01 maps to real owner service OpenAPI and validates JSON |
| Real IAM/OIDC, CSRF and BFF | **NOT IMPLEMENTED** | Authenticated server-only read/action, no cross-tenant disclosure |
| Task Intake/upload/READY | **NOT IMPLEMENTED** | Approved owner source, content provenance and immutable snapshot |
| Task coordinator (#18) | **CODE + 33 local CI tests, NOT DEPLOYED** | Trusted `issue_comment` workflow installed on default branch, actor-role identity bindings and real parallel GitHub tests |
| Dynamic PR path gate | **CODE + UNIT TESTS, NOT REQUIRED BY PROTECTED BRANCH** | Install on trusted base, make check required; test real PR denial |
| ADR-0002 source topology | **AWAITING OWNER APPROVAL** | Owner personally ratifies per SDD process |
| Browser integration E2E | **NOT RUN** | Real/fixture BFF browser tests on one merged SHA |
| Agent A01–A09 code ownership | **ALL INITIAL BACKLOG** | Only after coordinator grants actual lease; no fake claimed_at |

## I00 review A01–A09

- **A01** design accepted with security/source schema corrections; Issue #8.
- **A02** design accepted and PR #19 reconciled; Issue #9.
- **A03** design accepted RFQ + certificate wizard and 409 preflight; Issue #10.
- **A04–A09** work packets accepted for research; **no submitted code or own design result** in Issues #11–#16 at review. They cannot be marked implementation complete.
- All nine received individual [I00 Issue review comments](I00_A01_A09_REVIEW_20261028.md). No PR approvals or status claims are inferred.

## Honest launch recommendation

**GO NOW** for A01–A09 read-only source/API audits, design refinement, test specifications and own code-requirement requests under the separate task packets. **NO GO YET** for nine simultaneous claimed coding tasks: coordinator is not installed in default branch and distinct authenticated agent identity is unresolved (GitHub actions may all use one account). **NO GO** for production/external operations pending IAM, ADR and actual E2E.

A safe next milestone is owner-reviewed promotion of Studio docs and trusted coordinator workflow to default base, with GitHub identities mapped per agent, branch required checks and real CLAIM race test. Then freeze an agent coding C0 SHA and advance Issues to AVAILABLE (not directly CLAIMED).
