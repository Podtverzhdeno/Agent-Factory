package com.agentfactory.api;

import com.agentfactory.control.Ports;
import com.agentfactory.control.Protocol;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Proposed v0.1 direct service adapters. Explicitly instantiated only after
 * endpoint approval; never discovers/installs new services or leaks credentials.
 */
public final class RemoteHttpClients {
    private RemoteHttpClients() { }

    /** A token provider is mandatory; never use caller-supplied arbitrary bearer tokens. */
    @FunctionalInterface public interface ServiceTokens {
        String token(String service, String tenantId);
    }

    /** All configured hosts must be allowlisted. Plain HTTP is allowed solely for loopback integration tests. */
    public static final class Transport {
        private final RestClient client;
        private final URI base;
        private final String service;
        private final ServiceTokens tokens;
        private final ObjectMapper mapper;

        public Transport(String service, URI base, Set<String> allowedHosts, boolean testLoopbackHttp,
                         ServiceTokens tokens, ObjectMapper mapper) {
            this.service=Objects.requireNonNull(service);
            this.base=Objects.requireNonNull(base);
            this.tokens=Objects.requireNonNull(tokens);
            this.mapper=Objects.requireNonNull(mapper);
            String host=base.getHost();
            String scheme=base.getScheme();
            boolean isLoopback=host!=null &&
                (host.equalsIgnoreCase("localhost") || host.equals("127.0.0.1") || host.equals("[::1]"));
            boolean approved=host!=null && allowedHosts!=null &&
                allowedHosts.stream().anyMatch(allowed -> allowed!=null && allowed.equalsIgnoreCase(host));
            if (!approved || scheme==null || base.getUserInfo()!=null || base.getQuery()!=null ||
                base.getFragment()!=null || !(base.getPath().isEmpty() || base.getPath().equals("/")) ||
                !(scheme.equalsIgnoreCase("https") ||
                  (testLoopbackHttp && isLoopback && scheme.equalsIgnoreCase("http"))))
                throw new IllegalArgumentException("REMOTE_ENDPOINT_NOT_ALLOWLISTED");
            var http=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
                .followRedirects(HttpClient.Redirect.NEVER).build();
            var factory=new JdkClientHttpRequestFactory(http);
            factory.setReadTimeout(Duration.ofSeconds(10));
            this.client=RestClient.builder().requestFactory(factory).build();
        }
        Protocol.CommandReceipt submit(String path, String tenant, String idempotencyKey,
                                       String correlationId, String operationId, Map<String,?> json,
                                       String acceptedIdField) {
            String bearer=tokens.token(service,tenant);
            if(bearer==null || bearer.isBlank())
                throw new IllegalStateException("SERVICE_AUTH_NOT_CONFIGURED");
            URI target=base.resolve(path);
            return client.post().uri(target).contentType(MediaType.APPLICATION_JSON)
                .header("Authorization","Bearer "+bearer)
                .header("Idempotency-Key",idempotencyKey)
                .header("X-Correlation-ID",correlationId)
                .body(json).exchange((request,response)-> {
                    int status=response.getStatusCode().value();
                    if(status!=202) {
                        // No raw remote response body or credentials in error messages.
                        if(status==401 || status==403) throw new Protocol.RemoteCommandFailure("REMOTE_UNAUTHORIZED",false);
                        if(status==409 || status==400 || status==422)
                            throw new Protocol.RemoteCommandFailure("REMOTE_COMMAND_REJECTED",false);
                        throw new Protocol.RemoteCommandFailure("REMOTE_UNAVAILABLE",true);
                    }
                    JsonNode body;
                    try { body=mapper.readTree(response.getBody()); }
                    catch(Exception e) { throw new Protocol.RemoteCommandFailure("REMOTE_RECEIPT_INVALID",false); }
                    if(body==null || body.path(acceptedIdField).asText("").isBlank())
                        throw new Protocol.RemoteCommandFailure("REMOTE_RECEIPT_INVALID",false);
                    // Only Evaluation promises a caller-assigned run ID. Never accept
                    // a success receipt referencing somebody else's evaluation.
                    if ("evaluation_run_id".equals(acceptedIdField) &&
                        !operationId.equals(body.path(acceptedIdField).asText("")))
                        throw new Protocol.RemoteCommandFailure("REMOTE_RECEIPT_MISMATCH",false);
                    // v0.1 services may return a separate build/evaluation ID. If an
                    // operation_id is also echoed, it must match this exact command.
                    if (body.hasNonNull("operation_id") &&
                        !operationId.equals(body.path("operation_id").asText("")))
                        throw new Protocol.RemoteCommandFailure("REMOTE_RECEIPT_MISMATCH",false);
                    String remoteStatus=body.path("status").asText("");
                    if(!Set.of("QUEUED","RUNNING","ACCEPTED").contains(remoteStatus.toUpperCase(Locale.ROOT)))
                        throw new Protocol.RemoteCommandFailure("REMOTE_RECEIPT_INVALID",false);
                    return new Protocol.CommandReceipt(operationId,true);
                });
        }
    }

    public static Ports.BuildClient builder(Transport transport) {
        return c -> transport.submit("/internal/builds",c.tenantId(),c.idempotencyKey(),
            c.correlationId(),c.operationId(),Map.of(
                "schema_version","0.1","tenant_id",c.tenantId(),"task_snapshot_id",c.taskSnapshotId(),
                "snapshot_digest",c.snapshotDigest(),"idempotency_key",c.idempotencyKey(),
                "evaluation_policy_ref",c.policyRef(),"correlation_id",c.correlationId(),
                "operation_id",c.operationId()),"build_id");
    }

    public static Ports.EvaluationClient evaluator(Transport transport) {
        // Evaluation workstream 05 exposes a strict Pydantic DTO (extra=forbid).
        // evaluation_run_id is caller-assigned and must be echoed in the receipt.
        return c -> transport.submit("/internal/evaluations",c.tenantId(),c.idempotencyKey(),
            c.correlationId(),c.operationId(),Map.of(
                "tenant_id",c.tenantId(),"agent_spec_ref",c.specRef(),
                "agent_spec_digest",c.specDigest(),"dataset_version_ref",c.datasetRef(),
                "policy_ref",c.policyRef(),"idempotency_key",c.idempotencyKey(),
                "evaluation_run_id",c.operationId()),"evaluation_run_id");
    }

    public static Ports.OptimizationClient optimizer(Transport transport) {
        return c -> transport.submit("/internal/optimizations",c.tenantId(),c.idempotencyKey(),
            c.correlationId(),c.operationId(),Map.ofEntries(
                Map.entry("schema_version","0.1"),Map.entry("tenant_id",c.tenantId()),
                Map.entry("agent_spec_ref",c.specRef()),Map.entry("agent_spec_digest",c.specDigest()),
                Map.entry("baseline_spec_ref",c.baselineSpecRef()),
                Map.entry("baseline_spec_digest",c.baselineDigest()),
                Map.entry("train_validation_refs",c.datasetRef()),
                Map.entry("allowed_surfaces",c.allowedSurfaces()),
                Map.entry("idempotency_key",c.idempotencyKey()),
                Map.entry("correlation_id",c.correlationId()),
                Map.entry("operation_id",c.operationId())), "optimization_run_id");
    }
}
