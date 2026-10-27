package com.agentfactory.registry;

import java.util.UUID;

/** No Spring or Maven needed; exact HTTP telemetry allowlist and no-log-injection invariants. */
public final class RegistryTelemetryTest {
    private static int checks;
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }
    private static void rejects(Runnable action) {
        checks++;
        try { action.run(); throw new AssertionError("Expected invalid metadata rejection"); }
        catch (IllegalArgumentException expected) { /* correct */ }
    }
    public static void main(String[] args) {
        var routes = new String[][] {
            {"GET", "/v0/registry/manifests", "manifests.list"},
            {"POST", "/v0/registry/manifests", "manifests.register"},
            {"GET", "/v0/registry/audit", "audit.list"},
            {"GET", "/v0/registry/builder/manifests", "builder.list"},
            {"POST", "/v0/registry/select", "capabilities.select"},
            {"POST", "/v0/registry/payloads/validate", "payloads.validate"},
            {"POST", "/v0/registry/manifests/read.tool/1.0.0/execute/approve", "manifests.approve"},
            {"POST", "/v0/registry/manifests/read.tool/1.0.0/execute/revoke", "manifests.revoke"},
            {"POST", "/v0/registry/manifests/id-1/2.10.3-beta.1/execute/revoke", "manifests.revoke"},
        };
        for (String[] row : routes) check(row[2].equals(RegistryTelemetry.route(row[0],row[1])), "Expected finite route " + row[2]);
        var invalid = new String[][] {
            {"GET", "/v0/registry/select"},
            {"POST", "/v0/registry/audit"},
            {"POST", "/v0/registry/manifests/x/1.0.0/execute/approve?password=secret"},
            {"POST", "/v0/registry/manifests/x/1.0.0/execute/approve%0d%0aAuthorization:Bearer"},
            {"POST", "/v0/registry/manifests/x/01.0.0/execute/revoke"},
            {"POST", "/v0/registry/manifests/x/latest/execute/revoke"},
            {"POST", "/v0/registry/manifests/x/1.0.0/execute/unapprove"},
            {"POST", "/v0/registry/manifests/x/1.0.0/execute/approve/extra"},
            {"PUT", "/v0/registry/manifests"},
            {"GET", "/v0/registry/manifests/malicious?token=secret"},
        };
        for (String[] row : invalid) check("unmatched".equals(RegistryTelemetry.route(row[0],row[1])), "Do not dynamically label bad path");
        check("unmatched".equals(RegistryTelemetry.route(null, "/v0/registry/select")), "Null method safe");
        check("unmatched".equals(RegistryTelemetry.route("GET", null)), "Null path safe");
        String secret = "SensitiveTenantXYZSecretToken";
        UUID id = UUID.randomUUID();
        for (int status : new int[] {200,201,204,400,401,403,404,422,429,500,503}) {
            String log = RegistryTelemetry.eventLine(id,"POST", "/v0/registry/manifests/"+secret+"/1.0.0/execute/approve",status,9);
            check(log.contains("request_id=" + id) && log.contains("status=" + status)
                    && log.contains("status_class=" + status/100 + "xx") && log.contains("route=manifests.approve")
                    && !log.contains(secret) && !log.contains("Authorization") && !log.contains("Bearer"),
                "Metric line may contain only bounded internal values");
        }
        // Deterministic path/URL fuzzing: free-text identifiers and secrets are NEVER logged.
        var random = new java.util.Random(0x5AFE2026L);
        for (int i = 0; i < 750; i++) {
            StringBuilder malicious = new StringBuilder("sensitive_");
            int length = 3 + random.nextInt(180);
            for (int n = 0; n < length; n++) {
                String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-\n\r%?/=;&:";
                malicious.append(chars.charAt(random.nextInt(chars.length())));
            }
            String injected = malicious.toString();
            String line = RegistryTelemetry.eventLine(id, i % 2 == 0 ? "GET" : "POST",
                "/v0/registry/manifests/" + injected + "/1.0.0/execute/approve?jwt=SECRET", 401, i);
            check(!line.contains(injected) && !line.contains("SECRET")
                    && !line.contains("jwt=") && !line.contains("\n") && !line.contains("\r")
                    && line.contains("elapsed_ms=" + i), "Fuzz-safe low-cardinality logging");
        }
        // A fixed classifier must not grow its labels with the number of users or tools.
        var observedRoutes = new java.util.HashSet<String>();
        for (int i = 0; i < 250; i++) {
            String dynamicPath = "/v0/registry/manifests/tenant" + i + "/1.0.0/op/approve";
            observedRoutes.add(RegistryTelemetry.route("POST", dynamicPath));
            String emitted = RegistryTelemetry.eventLine(id, "POST", dynamicPath, 200, i);
            check(!emitted.contains("tenant" + i), "Never log user-supplied tool coordinates");
        }
        check(observedRoutes.equals(java.util.Set.of("manifests.approve")), "Stable cardinality for tool IDs");
        String good = RegistryTelemetry.eventLine(id,"POST", "/v0/registry/manifests/tool.a/1.0.0/execute/approve",200,0);
        check(good.contains("route=manifests.approve") && !good.contains("tool.a"), "Do not log tool ID");
        check(RegistryTelemetry.eventLine(id, "POST\nBearer secret", "/v0/registry/select",404,1).contains("method=OTHER route=unmatched"), "Sanitize method");
        for (var action : RegistryTelemetry.LifecycleAction.values()) {
            String lifecycle = RegistryTelemetry.lifecycleLine(id, action);
            check(lifecycle.equals("event=registry_lifecycle request_id=" + id + " action=" + action.name()),
                "Lifecycle log must have only a fixed action and server-generated correlation ID");
        }
        check(RegistryTelemetry.selectionLine(id, ToolRegistry.Decision.SELECTED, 3, 0)
            .equals("event=registry_selection request_id=" + id + " decision=SELECTED selected_count=3 denial_count=0"),
            "Safe selected cardinality");
        check(RegistryTelemetry.selectionLine(id, ToolRegistry.Decision.BLOCKED, 0, 10)
            .contains("decision=BLOCKED selected_count=0 denial_count=10"), "Safe blocked selection logging");
        rejects(() -> RegistryTelemetry.selectionLine(null, ToolRegistry.Decision.BLOCKED, 0, 0));
        rejects(() -> RegistryTelemetry.selectionLine(id, null, 0, 0));
        rejects(() -> RegistryTelemetry.selectionLine(id, ToolRegistry.Decision.SELECTED, -1, 0));
        rejects(() -> RegistryTelemetry.selectionLine(id, ToolRegistry.Decision.BLOCKED, 0, -1));
        rejects(() -> RegistryTelemetry.lifecycleLine(id, null));
        rejects(() -> RegistryTelemetry.eventLine(null,"GET","/",200,0));
        rejects(() -> RegistryTelemetry.eventLine(id,"GET","/",0,0));
        rejects(() -> RegistryTelemetry.eventLine(id,"GET","/",600,0));
        rejects(() -> RegistryTelemetry.eventLine(id,"GET","/",200,-1));
        System.out.println("PASS: " + checks + " telemetry tests — route cardinality, header safety, redaction and status classification");
    }
}
