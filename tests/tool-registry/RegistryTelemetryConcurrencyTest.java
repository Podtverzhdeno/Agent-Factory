package com.agentfactory.registry;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;

/** Concurrent logging must not share unsafe request metadata or leak untrusted input. */
public final class RegistryTelemetryConcurrencyTest {
    public static void main(String[] args) throws Exception {
        final int threads = 24;
        final int requestsPerThread = 100;
        final int requests = threads * requestsPerThread;
        try (var executor = Executors.newFixedThreadPool(threads)) {
            List<Callable<List<String>>> tasks = java.util.stream.IntStream.range(0, threads)
                .<Callable<List<String>>>mapToObj(thread -> () -> {
                    var output = new java.util.ArrayList<String>();
                    for (int n = 0; n < requestsPerThread; n++) {
                        UUID id = UUID.randomUUID();
                        String secret = "DO_NOT_LOG_TENANT_SECRET_" + thread + "_" + n;
                        String request = RegistryTelemetry.eventLine(id, "POST",
                            "/v0/registry/manifests/" + secret + "/1.0.0/execute/approve", 403, n);
                        if (!request.contains("request_id=" + id) || request.contains(secret)
                            || !request.contains("route=manifests.approve"))
                            throw new AssertionError("Mixed or leaked telemetry during concurrent request");
                        String lifecycle = RegistryTelemetry.lifecycleLine(id, RegistryTelemetry.LifecycleAction.REVOKED);
                        String selection = RegistryTelemetry.selectionLine(id, ToolRegistry.Decision.BLOCKED, 0, 2);
                        String rejection = RegistryTelemetry.rejectionLine(id, "FORBIDDEN");
                        if (!lifecycle.contains("request_id=" + id)
                            || !selection.contains("request_id=" + id)
                            || !rejection.contains("request_id=" + id))
                            throw new AssertionError("Correlation ID changed between event types");
                        output.add(id.toString());
                    }
                    return output;
                }).toList();
            var futures = executor.invokeAll(tasks);
            Set<String> seen = new HashSet<>();
            for (var future : futures) {
                for (String id : future.get()) {
                    if (!seen.add(id)) throw new AssertionError("Request correlation ID collision");
                }
            }
            if (seen.size() != requests) throw new AssertionError("Missing correlations");
            System.out.println("PASS: " + requests + " concurrent request correlations across 24 workers; unique and redacted");
        }
    }
}
