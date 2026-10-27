package com.agentfactory.registry;

import java.util.*;
import static com.agentfactory.registry.ToolRegistry.*;
import static com.agentfactory.registry.RegistrySelfTest.*;

/** Additional pure-domain negative cases runnable without Maven or infrastructure. */
public final class RegistryRegressionTest {
    private static int assertions;
    private static void check(boolean condition, String why) {
        assertions++;
        if (!condition) throw new AssertionError(why);
    }
    private static void reject(String code, Runnable run) {
        assertions++;
        try { run.run(); throw new AssertionError("Expected " + code); }
        catch (RegistryFailure error) {
            if (!error.code.equals(code)) throw new AssertionError("Expected " + code + ", got " + error.code);
        }
    }
    private static SelectionRequest pin(String capability, Map<String,String> versions) {
        return new SelectionRequest(Set.of(capability), Set.of(Effect.READ), Risk.LOW, versions, Map.of());
    }
    public static void main(String[] unused) {
        ToolRegistry registry = fixture();
        Manifest read = manifest("xlsx.read", "1.0.0", "read_xlsx", FILE_IN, ROWS,
            XLSX_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW);
        Manifest catalog = manifest("catalog.lookup", "1.0.0", "catalog_lookup", LOOKUP_IN, LOOKUP_OUT,
            CATALOG_ENDPOINT, Set.of(Effect.READ), Set.of("catalog:read"), Risk.LOW);
        register(registry, read);
        register(registry, catalog);

        // Pinning one tool must not veto unpinned tools.
        Selection partialPin = registry.select(user, new SelectionRequest(
            Set.of("read_xlsx", "catalog_lookup"), Set.of(Effect.READ), Risk.LOW,
            Map.of("xlsx.read", "1.0.0"), Map.of()));
        check(partialPin.decision() == Decision.SELECTED && partialPin.selectedTools().size() == 2,
            "Pin one tool, keep otherwise authorized tools");
        reject("INVALID_TASK", () -> registry.select(user, pin("read_xlsx", Map.of("xlsx.read", "latest"))));
        reject("INVALID_TASK", () -> registry.select(user, task()));
        reject("INVALID_TASK", () -> registry.select(user, null));
        reject("INVALID_MANIFEST", () -> registry.registerDraft(author, null));
        reject("INVALID_TASK", () -> registry.approve(reviewer, null, "1.0.0", "execute"));
        reject("INVALID_TASK", () -> registry.revoke(reviewer, "xlsx.read", "latest", "execute"));
        reject("INVALID_TASK", () -> registry.validatePayload(user, "xlsx.read", null, "execute", true, Map.of()));

        // Cannot publish an approved tool to another tenant through self-service registration.
        Manifest crossTenant = new Manifest("0.1", "shared.read", "1.0.0", "execute", Transport.MCP,
            Set.of("read_xlsx"), FILE_IN, ROWS, Set.of(Effect.READ), Set.of("xlsx:read"),
            Risk.LOW, Set.of("tenant-a", "tenant-b"), XLSX_ENDPOINT, Health.HEALTHY,
            "trusted:synthetic", "Read across tenants", "").withComputedDigest();
        reject("FORBIDDEN", () -> registry.registerDraft(author, crossTenant));
        check(registry.select(new Caller("builder-b", "tenant-b", user.scopes()), task("read_xlsx"))
            .denials().stream().noneMatch(d -> d.toolId().equals("xlsx.read")), "No cross-tenant tool ID leak");

        Caller aud = new Caller("auditor", "tenant-a", Set.of("registry:audit"));
        Caller otherAud = new Caller("auditor", "tenant-b", Set.of("registry:audit"));
        check(registry.auditTrail(aud).size() == 4, "Initial registration+approval audit");
        check(registry.auditTrail(otherAud).isEmpty(), "Tenant-bound audit isolation");
        reject("FORBIDDEN", () -> registry.auditTrail(user));
        String before = registry.select(user, task("read_xlsx")).registryRevision();
        registry.revoke(reviewer, "xlsx.read", "1.0.0", "execute");
        Selection revoked = registry.select(user, task("read_xlsx"));
        check(revoked.decision() == Decision.BLOCKED, "Revoked operation not returned to Builder");
        check(revoked.denials().stream().anyMatch(d -> d.code() == DenialCode.REVOKED && d.toolId().isEmpty()),
            "Revocation exposes typed denial without catalog metadata");
        check(registry.listApproved(user).stream().noneMatch(m -> m.toolId().equals("xlsx.read")),
            "Revoked operation removed from listing");
        check(!before.equals(registry.select(user, task("catalog_lookup")).registryRevision()),
            "Revocation changes snapshot revision");
        check(registry.auditTrail(aud).getLast().action().equals("REVOKED"), "Audit records revocation");
        reject("INVALID_STATE", () -> registry.revoke(reviewer, "xlsx.read", "1.0.0", "execute"));
        reject("IMMUTABLE", () -> registry.approve(reviewer, "xlsx.read", "1.0.0", "execute"));
        reject("NOT_APPROVED", () -> registry.validatePayload(user, "xlsx.read", "1.0.0", "execute", true,
            Map.of("file", "artifact://input")));
        reject("NOT_FOUND", () -> registry.revoke(new Caller("outsider", "tenant-b", Set.of("registry:approve")),
            "catalog.lookup", "1.0.0", "execute"));
        reject("NOT_FOUND", () -> registry.revoke(reviewer, "no-such", "1.0.0", "execute"));

        // Payload recursion: arrays of row objects enforce required fields, types, depth and size.
        registry.validatePayload(user, "catalog.lookup", "1.0.0", "execute", false,
            Map.of("items", List.of(Map.of("sku", "a", "price", 3.5))));
        reject("PAYLOAD_SCHEMA_MISMATCH", () -> registry.validatePayload(user,
            "catalog.lookup", "1.0.0", "execute", false,
            Map.of("items", List.of(Map.of("sku", "a", "price", "free")))));
        reject("PAYLOAD_SCHEMA_MISMATCH", () -> registry.validatePayload(user,
            "catalog.lookup", "1.0.0", "execute", false,
            Map.of("items", List.of(Map.of("sku", "a")))));
        reject("PAYLOAD_SCHEMA_MISMATCH", () -> registry.validatePayload(user,
            "catalog.lookup", "1.0.0", "execute", false,
            Map.of("items", List.of(Map.of("sku", "a", "price", 4, "secret", 1)))));
        reject("PAYLOAD_SCHEMA_MISMATCH", () -> registry.validatePayload(user,
            "catalog.lookup", "1.0.0", "execute", false,
            Map.of("items", List.of(Map.of("sku", "a", "price", Double.NaN)))));
        reject("PAYLOAD_SCHEMA_MISMATCH", () -> registry.validatePayload(user,
            "catalog.lookup", "1.0.0", "execute", false,
            Map.of("items", Collections.nCopies(513, Map.of("sku", "a", "price", 3)))));
        reject("PAYLOAD_SCHEMA_MISMATCH", () -> registry.validatePayload(user,
            "catalog.lookup", "1.0.0", "execute", true, Map.of("sku", "x".repeat(8193))));
        reject("INVALID_SCHEMA", () -> new Shape(Map.of("payload", FieldSpec.scalar(FieldType.STRING)),
            Set.of("payload"), true));
        reject("INVALID_SCHEMA", () -> FieldSpec.scalar(FieldType.OBJECT));
        reject("INVALID_SCHEMA", () -> FieldSpec.scalar(FieldType.ARRAY));

        // Version conflict under the same tool_id with two distinct operations.
        ToolRegistry versioned = fixture();
        Manifest older = new Manifest("0.1", "package", "1.0.0", "read", Transport.MCP,
            Set.of("read_xlsx"), FILE_IN, ROWS, Set.of(Effect.READ), Set.of("xlsx:read"),
            Risk.LOW, Set.of("tenant-a"), XLSX_ENDPOINT, Health.HEALTHY,
            "trusted:fixture", "Read package", "").withComputedDigest();
        Manifest newer = new Manifest("0.1", "package", "2.0.0", "catalog", Transport.MCP,
            Set.of("catalog_lookup"), LOOKUP_IN, LOOKUP_OUT, Set.of(Effect.READ), Set.of("catalog:read"),
            Risk.LOW, Set.of("tenant-a"), CATALOG_ENDPOINT, Health.HEALTHY,
            "trusted:fixture", "Catalog package", "").withComputedDigest();
        register(versioned, older); register(versioned, newer);
        Selection conflict = versioned.select(user, task("read_xlsx", "catalog_lookup"));
        check(conflict.decision() == Decision.BLOCKED && conflict.denials().stream()
            .anyMatch(d -> d.code() == DenialCode.INCOMPATIBLE_VERSIONS), "Conflict blocks mixed tool versions");

        // Search no longer fails solely because 19 trusted alternatives exist.
        ToolRegistry many = fixture();
        for (int i = 0; i < 30; i++) {
            register(many, manifest("alt." + i, "1.0.0", "read_xlsx", FILE_IN, ROWS,
                XLSX_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW));
        }
        Selection chosen = many.select(user, task("read_xlsx"));
        check(chosen.decision() == Decision.SELECTED && chosen.selectedTools().size() == 1,
            "Find exact single-tool minimum among 30 choices");
        check(chosen.selectedTools().getFirst().toolId().equals("alt.0"), "Deterministic tie break");

        // True least privilege minimizes the union of effective scopes, not a sum of duplicates.
        ToolRegistry minimumGrants = fixture();
        Manifest aRead = manifest("a.reader", "1.0.0", "read_xlsx", FILE_IN, ROWS,
            XLSX_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW);
        Manifest aCatalog = manifest("a.catalog", "1.0.0", "catalog_lookup", LOOKUP_IN, LOOKUP_OUT,
            CATALOG_ENDPOINT, Set.of(Effect.READ), Set.of("catalog:read"), Risk.LOW);
        Manifest zRead = manifest("z.reader", "1.0.0", "read_xlsx", FILE_IN, ROWS,
            XLSX_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW);
        Manifest zCatalog = manifest("z.catalog", "1.0.0", "catalog_lookup", LOOKUP_IN, LOOKUP_OUT,
            CATALOG_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW);
        for (Manifest m : List.of(aRead, aCatalog, zRead, zCatalog)) register(minimumGrants, m);
        Selection granted = minimumGrants.select(user, task("read_xlsx", "catalog_lookup"));
        Set<String> effective = new HashSet<>();
        granted.selectedTools().forEach(binding -> effective.addAll(binding.grantedScopes()));
        check(granted.decision() == Decision.SELECTED && effective.equals(Set.of("xlsx:read")),
            "Effective grants must contain only the minimal unique scope set");

        // A change in another tenant's register/approve cycle does not change our revision.
        ToolRegistry isolated = fixture();
        register(isolated, read);
        String baseline = isolated.select(user, task("read_xlsx")).registryRevision();
        Caller authorB = new Caller("author-b", "tenant-b", Set.of("registry:register"));
        Caller reviewerB = new Caller("reviewer-b", "tenant-b", Set.of("registry:approve"));
        Manifest other = new Manifest("0.1", "other.tool", "1.0.0", "execute", Transport.MCP,
            Set.of("catalog_lookup"), LOOKUP_IN, LOOKUP_OUT, Set.of(Effect.READ), Set.of("catalog:read"),
            Risk.LOW, Set.of("tenant-b"), CATALOG_ENDPOINT, Health.HEALTHY,
            "trusted:fixture", "Other tenant catalog", "").withComputedDigest();
        isolated.registerDraft(authorB, other);
        isolated.approve(reviewerB, "other.tool", "1.0.0", "execute");
        check(baseline.equals(isolated.select(user, task("read_xlsx")).registryRevision()),
            "Registry revision must be tenant-isolated");
        check(isolated.select(user, task("catalog_lookup")).denials().stream()
            .noneMatch(d -> d.toolId().equals("other.tool")), "Other tenant metadata stays private");
        check(isolated.auditTrail(new Caller("auditor-b", "tenant-b", Set.of("registry:audit")))
            .getFirst().sequence() == 1L, "Tenant-local audit sequence does not leak other tenants' history");
        // Two tenants may independently register identical tool/version/operation coordinates.
        Manifest sameIdentityB = new Manifest("0.1", read.toolId(), read.version(), read.operation(),
            read.transport(), read.capabilities(), read.inputSchemaRef(), read.outputSchemaRef(),
            read.sideEffects(), read.requiredScopes(), read.riskLevel(), Set.of("tenant-b"),
            read.endpointRef(), read.health(), "trusted:fixture", "Tenant B independent workbook reader", "")
            .withComputedDigest();
        isolated.registerDraft(authorB, sameIdentityB);
        isolated.approve(reviewerB, sameIdentityB.toolId(), sameIdentityB.version(), sameIdentityB.operation());
        Caller builderB = new Caller("builder-b", "tenant-b", user.scopes());
        check(isolated.select(builderB, task("read_xlsx")).decision() == Decision.SELECTED,
            "Same operation coordinates must work independently in tenant B");
        check(isolated.select(user, task("read_xlsx")).selectedTools().getFirst().manifestDigest()
                .equals(read.manifestDigest()), "Tenant B cannot overwrite tenant A manifest");
        isolated.revoke(reviewerB, read.toolId(), read.version(), read.operation());
        check(isolated.select(user, task("read_xlsx")).decision() == Decision.SELECTED,
            "Tenant B revocation cannot disable tenant A operation");
        check(isolated.select(builderB, task("read_xlsx")).decision() == Decision.BLOCKED,
            "Tenant-local revocation takes effect");
        reject("NOT_FOUND", () -> isolated.approve(reviewerB, "catalog.lookup", "1.0.0", "execute"));
        reject("UNAUTHENTICATED", () -> new Caller("builder", "tenant\nspoof", Set.of("registry:lookup")));
        check(isolated.select(builderB, task("catalog_lookup")).decision() == Decision.SELECTED,
            "Tenant B should retain its own catalogue implementation after a reader revocation");
        // Use a fresh tenant with no catalog to prove no cross-tenant capability-existence oracle.
        Caller builderC = new Caller("builder-c", "tenant-c", user.scopes());
        check(isolated.select(builderC, task("catalog_lookup")).denials().stream()
            .allMatch(d -> d.code() == DenialCode.NO_CAPABILITY),
            "Foreign tenant catalog contents must not be exposed through denial types");
        System.out.println("PASS: " + assertions + " additional registry security and lifecycle assertions");
    }
}
