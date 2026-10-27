package com.agentfactory.registry;

import java.util.*;
import java.util.stream.Collectors;
import static com.agentfactory.registry.ToolRegistry.Manifest;

/** Exact deterministic minimum cover with version consistency and bounded complexity. */
final class MinimumCapabilityCover {
    private static final int MAX_SEARCH_NODES = 250_000;
    record Result(List<Manifest> selected, boolean exhausted) {}
    private MinimumCapabilityCover() {}

    static Result find(List<Manifest> candidates, Set<String> required) {
        Search search = new Search(candidates, required);
        return new Result(search.find(), search.exhausted);
    }

    private static final class Search {
        private final List<Manifest> candidates;
        private final Set<String> required;
        private List<Manifest> best = List.of();
        private int nodes;
        private boolean exhausted;
        private Search(List<Manifest> candidates, Set<String> required) {
            this.candidates = candidates; this.required = new TreeSet<>(required);
        }
        List<Manifest> find() {
            explore(new ArrayList<>(), new TreeSet<>(), new TreeMap<>());
            return best;
        }
        private void explore(List<Manifest> chosen, Set<String> covered, Map<String, String> versions) {
            if (++nodes > MAX_SEARCH_NODES) { exhausted = true; return; }
            if (covered.containsAll(required)) {
                if (best.isEmpty() || compare(chosen, best) < 0) best = List.copyOf(chosen);
                return;
            }
            if (!best.isEmpty() && chosen.size() >= best.size()) return;
            String hardest = null; int count = Integer.MAX_VALUE;
            for (String capability : required) {
                if (covered.contains(capability)) continue;
                int options = 0;
                for (Manifest m : candidates) {
                    String pinned = versions.get(m.toolId());
                    if (m.capabilities().contains(capability) && (pinned == null || pinned.equals(m.version()))) options++;
                }
                if (options < count) { count = options; hardest = capability; }
            }
            if (count == 0 || hardest == null) return;
            for (Manifest candidate : candidates) {
                if (exhausted) return;
                if (!candidate.capabilities().contains(hardest) || chosen.contains(candidate)) continue;
                String pinned = versions.get(candidate.toolId());
                if (pinned != null && !pinned.equals(candidate.version())) continue;
                chosen.add(candidate);
                Set<String> next = new TreeSet<>(covered); next.addAll(candidate.capabilities());
                Map<String, String> pins = new TreeMap<>(versions);
                pins.put(candidate.toolId(), candidate.version());
                explore(chosen, next, pins);
                chosen.removeLast();
            }
        }
    }
    private static int compare(List<Manifest> a, List<Manifest> b) {
        int v = Integer.compare(a.size(), b.size()); if (v != 0) return v;
        v = Integer.compare(a.stream().mapToInt(m -> m.riskLevel().ordinal()).sum(), b.stream().mapToInt(m -> m.riskLevel().ordinal()).sum());
        if (v != 0) return v;
        // Least authority means minimizing the *distinct* permissions needed by the
        // complete binding set, not counting repeated scopes as separate grants.
        v = Integer.compare(uniqueScopes(a).size(), uniqueScopes(b).size());
        if (v != 0) return v;
        v = Integer.compare(a.stream().mapToInt(m -> m.sideEffects().size()).sum(), b.stream().mapToInt(m -> m.sideEffects().size()).sum());
        if (v != 0) return v;
        return signature(a).compareTo(signature(b));
    }
    private static Set<String> uniqueScopes(List<Manifest> selected) {
        Set<String> scopes = new HashSet<>();
        for (Manifest manifest : selected) scopes.addAll(manifest.requiredScopes());
        return scopes;
    }
    private static String signature(List<Manifest> x) {
        return x.stream().map(m -> m.toolId() + "@" + m.version() + "/" + m.operation()).sorted().collect(Collectors.joining("|"));
    }
}
