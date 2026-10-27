package com.agentfactory.registry;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

import static com.agentfactory.registry.ToolRegistry.*;

/**
 * Proposed v0 compatibility projection for the Agent Builder's read-only ToolManifest port.
 * No network calls, privilege grants, credential fields or approval mutations are performed.
 *
 * Builder v0 lacks an operation coordinate and rejects CRITICAL risk. Only the unambiguous
 * execute operation is projected; all other operations fail closed until a shared contract
 * explicitly adds operation to the immutable AgentSpec binding.
 */
public final class BuilderManifestProjection {
    private BuilderManifestProjection() {}

    public record Item(String toolId, String version, String manifestDigest,
                       Set<String> capabilities, Set<String> sideEffects,
                       Set<String> requiredScopes, Set<String> tenantAvailability,
                       String inputSchemaRef, String outputSchemaRef,
                       String riskLevel, boolean approved, String transport) {
        public Item {
            capabilities = immutableSorted(capabilities);
            sideEffects = immutableSorted(sideEffects);
            requiredScopes = immutableSorted(requiredScopes);
            tenantAvailability = immutableSorted(tenantAvailability);
        }
    }

    public static List<Item> eligible(ToolRegistry registry, Caller caller) {
        List<Item> result = new ArrayList<>();
        for (Manifest manifest : registry.listApproved(caller)) {
            if (manifest.riskLevel() == Risk.CRITICAL || !"execute".equals(manifest.operation())) {
                continue;
            }
            Set<String> effects = new TreeSet<>();
            for (Effect effect : manifest.sideEffects()) {
                effects.add(effect.name().toLowerCase(Locale.ROOT));
            }
            result.add(new Item(manifest.toolId(), manifest.version(), manifest.manifestDigest(),
                manifest.capabilities(), effects, manifest.requiredScopes(),
                manifest.tenantAvailability(), manifest.inputSchemaRef(), manifest.outputSchemaRef(),
                manifest.riskLevel().name().toLowerCase(Locale.ROOT), true, manifest.transport().name()));
        }
        // No silent truncation: Builder v0 refuses catalogues larger than 18 entries.
        if (result.size() > 18) {
            throw new ToolRegistry.RegistryFailure("BUILDER_PORT_CAPACITY",
                "Builder v0 requires narrower capability selection");
        }
        result.sort(java.util.Comparator.comparing(Item::toolId).thenComparing(Item::version));
        return List.copyOf(result);
    }

    private static Set<String> immutableSorted(Set<String> source) {
        return Collections.unmodifiableSet(new TreeSet<>(source));
    }
}
