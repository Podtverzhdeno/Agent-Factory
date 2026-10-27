package com.agentfactory.registry;

import java.util.List;
import java.util.Set;

import static com.agentfactory.registry.ToolRegistry.*;
import static com.agentfactory.registry.RegistrySelfTest.*;

/** Contract fixture aligned with agent/04-agent-engine/agent_builder/core.py ToolManifest. */
public final class RegistryBuilderProjectionTest {
    private RegistryBuilderProjectionTest() {}

    public static void main(String[] args) {
        ToolRegistry registry = fixture();
        register(registry, manifest("xlsx.read", "1.0.0", "read_xlsx", FILE_IN, ROWS,
            XLSX_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW));
        register(registry, manifest("catalog.lookup", "1.0.0", "catalog_lookup", LOOKUP_IN,
            LOOKUP_OUT, CATALOG_ENDPOINT, Set.of(Effect.READ), Set.of("catalog:read"), Risk.LOW));
        register(registry, manifest("xlsx.write", "1.0.0", "write_xlsx", WRITE_IN,
            FILE_OUT, XLSX_ENDPOINT, Set.of(Effect.DRAFT_FILE), Set.of("xlsx:draft"), Risk.LOW));
        register(registry, manifest("payments.charge", "1.0.0", "charge_card", PAY_IN,
            PAY_OUT, PAY_ENDPOINT, Set.of(Effect.PAYMENT), Set.of("payments:charge"), Risk.CRITICAL));

        List<BuilderManifestProjection.Item> all = BuilderManifestProjection.eligible(registry, user);
        assertEquals(3, all.size(), "RFQ tools count");
        assertEquals(List.of("catalog.lookup", "xlsx.read", "xlsx.write"),
            all.stream().map(BuilderManifestProjection.Item::toolId).toList(), "stable order");
        for (var item : all) {
            assertTrue(item.approved(), "only approved entries");
            assertEquals("low", item.riskLevel(), "lower-case Builder risk");
            assertEquals("MCP", item.transport(), "Builder transport");
            assertTrue(item.manifestDigest().matches("sha256:[0-9a-f]{64}"), "digest pin");
            assertEquals(Set.of("tenant-a"), item.tenantAvailability(), "tenant scope");
            assertTrue(item.sideEffects().stream().allMatch(s -> s.equals("read") || s.equals("draft_file")),
                "lower-case side effects");
        }
        assertTrue(all.stream().noneMatch(v -> v.toolId().contains("payment")), "payments not projected");
        assertEquals(0, BuilderManifestProjection.eligible(registry,
            new Caller("other", "tenant-b", user.scopes())).size(), "no foreign tenant tool");
        assertEquals(0, BuilderManifestProjection.eligible(registry,
            new Caller("reader", "tenant-a", Set.of("registry:lookup"))).size(), "missing scope");

        Manifest searchOp = new Manifest("0.1", "catalog.search", "1.0.0", "search_items",
            Transport.MCP, Set.of("catalog_lookup"), LOOKUP_IN, LOOKUP_OUT,
            Set.of(Effect.READ), Set.of("catalog:read"), Risk.LOW, Set.of("tenant-a"),
            CATALOG_ENDPOINT, Health.HEALTHY, "trusted:synthetic-fixture",
            "Search operation requiring Builder contract update", "").withComputedDigest();
        register(registry, searchOp);
        assertTrue(BuilderManifestProjection.eligible(registry, user).stream()
            .noneMatch(v -> v.toolId().equals("catalog.search")), "unmodelled operation must fail closed");
        System.out.println("PASS: Builder v0 projection enforces tenant/scopes, risk compatibility and operation restriction");
    }

    private static void assertTrue(boolean yes, String description) {
        if (!yes) throw new AssertionError(description);
    }
    private static void assertEquals(Object expected, Object actual, String description) {
        if (!expected.equals(actual)) {
            throw new AssertionError(description + ": expected " + expected + ", actual " + actual);
        }
    }
}
