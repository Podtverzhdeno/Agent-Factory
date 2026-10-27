package com.agentfactory.registry;

import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Low-cardinality, privacy-preserving operational events.
 * This code deliberately does not accept request bodies, headers, tenants, JWTs,
 * actor names, manifest descriptions, paths or tool IDs as log field values.
 * Domain audit events are authoritative only after a durable database is approved.
 */
final class RegistryTelemetry {
    private static final Set<String> METHODS = Set.of("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS");
    private static final Pattern MANIFEST_MUTATION = Pattern.compile(
        "^/v0/registry/manifests/[A-Za-z][A-Za-z0-9_.:-]{0,127}/"
          + "(?:0|[1-9][0-9]*)\\.(?:0|[1-9][0-9]*)\\.(?:0|[1-9][0-9]*)"
          + "(?:-[A-Za-z0-9.-]+)?/[A-Za-z][A-Za-z0-9_.:-]{0,127}/(approve|revoke)$");

    private RegistryTelemetry() {}

    static String route(String method, String path) {
        if (method == null || path == null) return "unmatched";
        return switch (method) {
            case "GET" -> switch (path) {
                case "/v0/registry/manifests" -> "manifests.list";
                case "/v0/registry/audit" -> "audit.list";
                case "/v0/registry/builder/manifests" -> "builder.list";
                default -> "unmatched";
            };
            case "POST" -> switch (path) {
                case "/v0/registry/manifests" -> "manifests.register";
                case "/v0/registry/select" -> "capabilities.select";
                case "/v0/registry/payloads/validate" -> "payloads.validate";
                default -> {
                    var match = MANIFEST_MUTATION.matcher(path);
                    if (!match.matches()) yield "unmatched";
                    yield "approve".equals(match.group(1)) ? "manifests.approve" : "manifests.revoke";
                }
            };
            default -> "unmatched";
        };
    }

    static String eventLine(UUID requestId, String method, String path, int status, long elapsedMillis) {
        if (requestId == null || elapsedMillis < 0 || status < 100 || status > 599)
            throw new IllegalArgumentException("Invalid internally measured request metadata");
        String methodLabel = METHODS.contains(method) ? method : "OTHER";
        return "event=registry_http_request request_id=" + requestId
            + " method=" + methodLabel + " route=" + route(methodLabel, path)
            + " status=" + status + " status_class=" + (status / 100) + "xx"
            + " elapsed_ms=" + elapsedMillis;
    }
}
