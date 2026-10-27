package com.agentfactory.registry;

import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

import static com.agentfactory.registry.ToolRegistry.*;

/** Experimental REST boundary: tenant and grants come exclusively from validated JWT, never request JSON. */
@RestController
@RequestMapping("/v0/registry")
public final class RegistryApi {
    private static final Logger LOG = LoggerFactory.getLogger(RegistryApi.class);
    private final ToolRegistry registry;
    public RegistryApi(ToolRegistry registry) { this.registry = registry; }

    @PostMapping("/manifests")
    public ResponseEntity<Map<String,String>> draft(@AuthenticationPrincipal Jwt jwt, @RequestBody Manifest manifest) {
        registry.registerDraft(caller(jwt), manifest);
        LOG.info("{}", RegistryTelemetry.lifecycleLine(correlationId(), RegistryTelemetry.LifecycleAction.REGISTERED));
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("status","DRAFT","digest",manifest.manifestDigest()));
    }
    @PostMapping("/manifests/{toolId}/{version}/{operation}/approve")
    public Map<String,String> approve(@AuthenticationPrincipal Jwt jwt, @PathVariable String toolId,
                                      @PathVariable String version, @PathVariable String operation) {
        registry.approve(caller(jwt),toolId,version,operation);
        LOG.info("{}", RegistryTelemetry.lifecycleLine(correlationId(), RegistryTelemetry.LifecycleAction.APPROVED));
        return Map.of("status","APPROVED");
    }
    @PostMapping("/manifests/{toolId}/{version}/{operation}/revoke")
    public Map<String,String> revoke(@AuthenticationPrincipal Jwt jwt, @PathVariable String toolId,
                                     @PathVariable String version, @PathVariable String operation) {
        registry.revoke(caller(jwt), toolId, version, operation);
        LOG.info("{}", RegistryTelemetry.lifecycleLine(correlationId(), RegistryTelemetry.LifecycleAction.REVOKED));
        return Map.of("status", "REVOKED");
    }
    @GetMapping("/audit")
    public List<AuditEvent> audit(@AuthenticationPrincipal Jwt jwt) {
        return registry.auditTrail(caller(jwt));
    }
    @GetMapping("/manifests")
    public List<Manifest> list(@AuthenticationPrincipal Jwt jwt) { return registry.listApproved(caller(jwt)); }

    /** Read-only Builder v0 compatibility view; no tool execution or new grants. */
    @GetMapping("/builder/manifests")
    public List<BuilderManifestProjection.Item> builderManifests(@AuthenticationPrincipal Jwt jwt) {
        return BuilderManifestProjection.eligible(registry, caller(jwt));
    }

    @PostMapping("/select")
    public Selection select(@AuthenticationPrincipal Jwt jwt, @RequestBody SelectionRequest request) {
        Selection selected = registry.select(caller(jwt),request);
        LOG.info("{}", RegistryTelemetry.selectionLine(correlationId(), selected.decision(),
            selected.selectedTools().size(), selected.denials().size()));
        return selected;
    }
    public record PayloadCheck(String toolId, String version, String operation, boolean input, Map<String,Object> payload) {}
    @PostMapping("/payloads/validate")
    public Map<String,Boolean> validate(@AuthenticationPrincipal Jwt jwt, @RequestBody PayloadCheck request) {
        registry.validatePayload(caller(jwt),request.toolId(),request.version(),request.operation(),request.input(),request.payload());
        return Map.of("valid",true);
    }
    private static UUID correlationId() {
        String stored = MDC.get("request_id");
        if (stored != null) {
            try { return UUID.fromString(stored); }
            catch (IllegalArgumentException ignored) { /* Never trust arbitrary MDC content. */ }
        }
        return UUID.randomUUID();
    }

    private static Caller caller(Jwt jwt) {
        if (jwt == null) throw new RegistryFailure("UNAUTHENTICATED","Bearer JWT required");
        String tenant = jwt.getClaimAsString("tenant_id");
        Object raw = jwt.getClaims().get("scope");
        Set<String> scopes = raw instanceof String s && !s.isBlank() ? new HashSet<>(Arrays.asList(s.strip().split("\\s+"))) : Set.of();
        return new Caller(jwt.getSubject(),tenant,scopes);
    }
    @ExceptionHandler(RegistryFailure.class)
    public ResponseEntity<Map<String,Object>> onRegistryError(RegistryFailure error) {
        HttpStatus status = switch (error.code) {
            case "FORBIDDEN", "SEPARATION_OF_DUTIES" -> HttpStatus.FORBIDDEN;
            case "UNAUTHENTICATED" -> HttpStatus.UNAUTHORIZED;
            case "NOT_FOUND" -> HttpStatus.NOT_FOUND;
            case "VERSION_EXISTS", "IMMUTABLE", "INVALID_STATE" -> HttpStatus.CONFLICT;
            case "CAPACITY_EXCEEDED" -> HttpStatus.SERVICE_UNAVAILABLE;
            default -> HttpStatus.UNPROCESSABLE_ENTITY;
        };
        return ResponseEntity.status(status).body(Map.of("code", error.code, "detail", error.getMessage(),
            "retryable", false, "trace_id", UUID.randomUUID().toString(), "required_action", "Review registry policy or manifest"));
    }
}
