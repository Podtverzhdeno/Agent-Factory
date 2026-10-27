# Dependency support gate — workstream 03

**Review date:** 2026-10-27. **Status: MIGRATION PREPARED; MAVEN VERIFICATION AND RELEASE BLOCKED.**

The module POM now targets Spring Boot `4.1.2` (GA October 23, 2026); the previous baseline was `3.4.7`. The Spring Boot 3.4 branch is outside its OSS security-support period (ended 2025-12-31); extended commercial support is not established for this project. See the vendor's support policy: https://github.com/spring-projects/spring-boot/wiki/Supported-Versions ; release status: https://endoflife.date/spring-boot ; advisories: https://spring.io/security/ .

**Risk:** vulnerability fixes may no longer reach the pinned public patch line. The module uses Spring MVC and Spring Security resource-server features. This is a support-policy finding, *not* a claim that any particular listed CVE has been proven exploitable in this specific module.

**Required remediation before deployment:**

1. Select an actively OSS-supported Spring Boot release under owner-approved dependency policy (4.1.x was supported at this review date). Do not assume a 3.x -> 4.x update is binary compatible.
2. Verify Spring MVC/Security/Jackson package and configuration migrations, including test auto-configuration annotations and JWT validators.
3. Execute `mvn -f services/tool-mcp-registry/pom.xml clean verify` on the chosen Java toolchain. Require independently passing unit/MVC/JWT-denial tests and an SBOM/vulnerability scan with documented exceptions.
4. Run the standalone Java security and contract suites, tenant authorization tests and production-candidate dependency audit again on the *same commit*. Record actual CI URLs and commit SHA.
5. Complete ADR-0002, durable audit and tenant storage review, endpoint/JWKS attestation, and Builder/Runtime interoperability before changing PR Draft to reviewable.

The supported-version dependency update, Web MVC starters, Jackson 3 configuration and MVC test import migration are prepared. **Do not mark the migration complete without running Maven/JUnit on the exact commit.** Service deployment remains blocked pending owner ADR and security review.
