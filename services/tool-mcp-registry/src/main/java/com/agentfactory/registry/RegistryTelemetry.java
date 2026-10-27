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

    enum LifecycleAction { REGISTERED, APPROVED, REVOKED }

    private RegistryTelemetry() {}

    /** Only bounded typed decision metadata, never capability names or denial details. */
    static String selectionLine(UUID requestId, ToolRegistry.Decision decision, int selectedCount, int denialCount) {
        if (requestId == null || decision == null || selectedCount < 0 || denialCount < 0)
            throw new IllegalArgumentException("Invalid selection metadata");
        return "event=registry_selection request_id=" + requestId + " decision=" + decision.name()
            + " selected_count=" + selectedCount + " denial_count=" + denialCount;
    }

    /** Low-cardinality error grouping; never log free-text exception messages or unbounded codes. */
    static String rejectionLine(UUID requestId, String code) {
        if (requestId == null) throw new IllegalArgumentException("Missing correlation id");
        String group = switch (code == null ? "" : code) {
            case "FORBIDDEN", "SEPARATION_OF_DUTIES", "UNAUTHENTICATED", "MISSING_PERMISSION" -> "AUTHORIZATION";
            case "NOT_FOUND", "NOT_APPROVED" -> "ABSENT";
            case "VERSION_EXISTS", "IMMUTABLE", "INVALID_STATE" -> "CONFLICT";
            case "ENDPOINT_UNVERIFIED", "UNTRUSTED_PROVENANCE", "INVALID_DIGEST" -> "TRUST";
            case "SEARCH_LIMIT", "CAPACITY_EXCEEDED" -> "CAPACITY";
            case "INVALID_SCHEMA", "INVALID_TASK", "INVALID_MANIFEST", "INVALID_SCOPES",
                 "MALICIOUS_DESCRIPTION", "INVALID_VERSION", "INVALID_EFFECTS", "RISK_UNDERSTATED" -> "VALIDATION";
            default -> "OTHER";
        };
        return "event=registry_rejection request_id=" + requestId + " category=" + group;
    }

    /** Informational lifecycle logs are NOT an authoritative or durable audit record. */
    static String lifecycleLine(UUID requestId, LifecycleAction action) {
        if (requestId == null || action == null) throw new IllegalArgumentException("Invalid lifecycle metadata");
        return "event=registry_lifecycle request_id=" + requestId + " action=" + action.name();
    }


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
