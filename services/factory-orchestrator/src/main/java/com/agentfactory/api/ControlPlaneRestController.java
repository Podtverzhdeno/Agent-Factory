package com.agentfactory.api;

import com.agentfactory.control.ControlPlane;
import com.agentfactory.control.Protocol;
import com.agentfactory.control.Workflow;
import java.util.Arrays;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

/**
 * REST adapter for the proposed contracts. Trusted tenant and scopes derive
 * only from a validated JWT; callers cannot elevate rights via payload fields.
 */
@RestController
public class ControlPlaneRestController {
    private final ControlPlane control;
    public ControlPlaneRestController(ControlPlane control) { this.control = control; }

    private Protocol.Principal principal(Jwt jwt) {
        if (jwt == null) throw new IllegalStateException("UNAUTHENTICATED");
        String tenant = jwt.getClaimAsString("tenant_id");
        String scope = jwt.getClaimAsString("scope");
        Set<String> scopes = scope == null ? Set.of() : Arrays.stream(scope.split(" "))
            .filter(s -> !s.isBlank()).collect(Collectors.toUnmodifiableSet());
        return new Protocol.Principal(jwt.getSubject(), tenant, scopes);
    }

    public record IdempotentAction(String idempotencyKey) { }
    public record TrainingAction(String rightsRef, String idempotencyKey) { }

    @PostMapping("/v1/workflows")
    public ResponseEntity<Workflow.View> start(@AuthenticationPrincipal Jwt jwt,
                                                @RequestBody Protocol.Start request) {
        return ResponseEntity.accepted().body(control.start(principal(jwt),request));
    }
    @GetMapping("/v1/workflows/{workflowId}")
    public Workflow.View get(@AuthenticationPrincipal Jwt jwt,
                             @PathVariable String workflowId, @RequestParam String tenantId) {
        return control.get(principal(jwt),tenantId,workflowId);
    }
    @GetMapping("/v1/workflows/{workflowId}/audit")
    public java.util.List<Workflow.Audit> audit(@AuthenticationPrincipal Jwt jwt,
                                                 @PathVariable String workflowId,
                                                 @RequestParam String tenantId) {
        return control.audit(principal(jwt),tenantId,workflowId);
    }
    @PostMapping("/v1/workflows/{workflowId}/release")
    public Workflow.View release(@AuthenticationPrincipal Jwt jwt, @PathVariable String workflowId,
                                 @RequestParam String tenantId, @RequestBody IdempotentAction action) {
        return control.release(principal(jwt),tenantId,workflowId,action.idempotencyKey());
    }
    @PostMapping("/v1/workflows/{workflowId}/rollback")
    public Workflow.View rollback(@AuthenticationPrincipal Jwt jwt, @PathVariable String workflowId,
                                  @RequestParam String tenantId, @RequestBody IdempotentAction action) {
        return control.rollback(principal(jwt),tenantId,workflowId,action.idempotencyKey());
    }
    @PostMapping("/v1/workflows/{workflowId}/train")
    public Workflow.View train(@AuthenticationPrincipal Jwt jwt, @PathVariable String workflowId,
                               @RequestParam String tenantId, @RequestBody TrainingAction action) {
        return control.requestSoup(principal(jwt),tenantId,workflowId,action.rightsRef(),action.idempotencyKey());
    }
    @PostMapping("/internal/events/build")
    public Workflow.View buildEvent(@AuthenticationPrincipal Jwt jwt,
                                    @RequestBody Protocol.BuildFinished event) {
        return control.onBuild(principal(jwt),event);
    }
    @PostMapping("/internal/events/evaluation")
    public Workflow.View evaluationEvent(@AuthenticationPrincipal Jwt jwt,
                                         @RequestBody Protocol.EvaluationFinished event) {
        return control.onEvaluation(principal(jwt),event);
    }
    @PostMapping("/internal/events/soup")
    public Workflow.View soupEvent(@AuthenticationPrincipal Jwt jwt,
                                   @RequestBody Protocol.SoupFinished event) {
        return control.onSoup(principal(jwt),event);
    }
    @PostMapping("/internal/events/optimization")
    public Workflow.View optimizationEvent(@AuthenticationPrincipal Jwt jwt,
                                           @RequestBody Protocol.OptimizationFinished event) {
        return control.onOptimization(principal(jwt),event);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<Map<String,String>> invalidRequest(IllegalArgumentException error) {
        return ResponseEntity.badRequest().body(Map.of("code","INVALID_REQUEST","retryable","false"));
    }

    @ExceptionHandler(java.util.NoSuchElementException.class)
    ResponseEntity<Map<String,String>> missingWorkflow(java.util.NoSuchElementException error) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(Map.of("code","WORKFLOW_NOT_FOUND","retryable","false"));
    }

    @ExceptionHandler(IllegalStateException.class)
    ResponseEntity<Map<String,String>> businessError(IllegalStateException error) {
        String raw = error.getMessage();
        String code = raw != null && raw.matches("[A-Z0-9_]{2,80}") ? raw : "WORKFLOW_REJECTED";
        HttpStatus status = code.equals("UNAUTHENTICATED") ? HttpStatus.UNAUTHORIZED
            : code.startsWith("UNAUTHORIZED") ? HttpStatus.FORBIDDEN : HttpStatus.CONFLICT;
        boolean retryable = code.equals("EVENT_AWAITING_COMMAND_RECEIPT");
        return ResponseEntity.status(status).body(Map.of("code",code,"retryable",Boolean.toString(retryable)));
    }
}
