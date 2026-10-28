# Agent Factory Studio · C0-prep

This branch is **not frozen C0**: no IAM, BFF, true customer data, lockfile, production services or integration tests. Local protected operator and workspace layouts deny all requests until real server-owned authorization is wired.

Proposed stack: Next.js 16.4.3, React 19.3.0, TS strict, SCSS Modules. For a reproducible C0, I00 must generate and commit a lockfile, audit versions, run npm install/typecheck/lint/build and validate the actual app. Dependencies and builds in GitHub are not proven by these source files.

**Ports:** `@studio/contracts`, `@studio/api`, `@studio/ui`, `@studio/charts`, `@studio/auth` alias to intentionally minimal I00-owned code. A01/A02 will replace the implementations under their exclusive directories through integrator-controlled alias update. Browser→internal-service direct access is prohibited.
