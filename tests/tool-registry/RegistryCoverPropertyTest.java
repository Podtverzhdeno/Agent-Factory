package com.agentfactory.registry;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

import static com.agentfactory.registry.ToolRegistry.*;

/** Deterministic randomized checks against an independent brute-force set-cover oracle. */
public final class RegistryCoverPropertyTest {
    private RegistryCoverPropertyTest() {}

    public static void main(String[] args) {
        Random random = new Random(0xA6E17L);
        for (int run = 0; run < 500; run++) {
            int n = 1 + random.nextInt(10);
            List<Manifest> candidates = new ArrayList<>();
            Set<String> needed = Set.of("cap.a", "cap.b", "cap.c", "cap.d");
            for (int i = 0; i < n; i++) {
                Set<String> capabilities = new TreeSet<>();
                for (String capability : needed) {
                    if (random.nextBoolean()) capabilities.add(capability);
                }
                if (capabilities.isEmpty()) capabilities.add("cap.a");
                String id = "tool." + random.nextInt(5);
                String version = random.nextBoolean() ? "1.0.0" : "2.0.0";
                Set<String> scopes = random.nextBoolean() ? Set.of("read:items") : Set.of("read:items", "read:details");
                Set<Effect> effects = random.nextBoolean() ? Set.of(Effect.READ) : Set.of(Effect.READ, Effect.DRAFT_FILE);
                Risk risk = random.nextBoolean() ? Risk.LOW : Risk.MEDIUM;
                candidates.add(new Manifest("0.1", id, version, "op." + i, Transport.LOCAL,
                    capabilities, "artifact://schemas/input", "artifact://schemas/output", effects, scopes,
                    risk, Set.of("tenant-a"), "artifact://approved/endpoints/fixture", Health.HEALTHY,
                    "trusted:fixture", "Synthetic property case", "sha256:fixture"));
            }
            candidates.sort(Comparator.comparing(Manifest::toolId).thenComparing(Manifest::version)
                .thenComparing(Manifest::operation));
            List<Manifest> brute = oracle(candidates, needed);
            MinimumCapabilityCover.Result actual = MinimumCapabilityCover.find(candidates, needed);
            if (actual.exhausted() || !signature(brute).equals(signature(actual.selected()))) {
                throw new AssertionError("Minimum-cover mismatch at seed-run " + run
                    + "; expected=" + signature(brute) + "; actual=" + signature(actual.selected()));
            }
        }
        System.out.println("PASS: 500 deterministic property cases agree with independent exhaustive cover oracle");
    }

    private static List<Manifest> oracle(List<Manifest> candidates, Set<String> required) {
        List<Manifest> best = List.of();
        for (int mask = 1; mask < (1 << candidates.size()); mask++) {
            List<Manifest> subset = new ArrayList<>();
            Map<String, String> versions = new HashMap<>();
            Set<String> coverage = new HashSet<>();
            boolean conflict = false;
            for (int i = 0; i < candidates.size(); i++) {
                if ((mask & (1 << i)) == 0) continue;
                Manifest manifest = candidates.get(i);
                subset.add(manifest);
                coverage.addAll(manifest.capabilities());
                String existing = versions.putIfAbsent(manifest.toolId(), manifest.version());
                if (existing != null && !existing.equals(manifest.version())) conflict = true;
            }
            if (conflict || !coverage.containsAll(required)) continue;
            if (best.isEmpty() || compare(subset, best) < 0) best = List.copyOf(subset);
        }
        return best;
    }

    private static int compare(List<Manifest> first, List<Manifest> second) {
        int result = Integer.compare(first.size(), second.size());
        if (result != 0) return result;
        result = Integer.compare(first.stream().mapToInt(x -> x.riskLevel().ordinal()).sum(),
            second.stream().mapToInt(x -> x.riskLevel().ordinal()).sum());
        if (result != 0) return result;
        result = Integer.compare(first.stream().mapToInt(x -> x.requiredScopes().size()).sum(),
            second.stream().mapToInt(x -> x.requiredScopes().size()).sum());
        if (result != 0) return result;
        result = Integer.compare(first.stream().mapToInt(x -> x.sideEffects().size()).sum(),
            second.stream().mapToInt(x -> x.sideEffects().size()).sum());
        return result != 0 ? result : signature(first).compareTo(signature(second));
    }

    private static String signature(List<Manifest> manifests) {
        return manifests.stream().map(x -> x.toolId() + "@" + x.version() + "/" + x.operation())
            .sorted().collect(Collectors.joining("|"));
    }
}
