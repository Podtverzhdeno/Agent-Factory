package com.agentfactory.api;

import com.agentfactory.control.OutboxDispatcher;
import com.agentfactory.control.Ports;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

/**
 * Deliberate opt-in only: no production topology, service credentials, or network
 * endpoints are selected until owner ADR-0002 and service owners' approval.
 * Requires an independently provided service-token bean; there is no insecure default.
 */
@Configuration
@Profile("remote-poc")
@ConditionalOnProperty(prefix="factory.remote",name="enabled",havingValue="true")
public class RemoteProofOfConceptConfiguration {
    @Bean Ports.BuildClient remoteBuilder(
        @Value("${factory.remote.builder-uri}") URI endpoint,
        @Value("${factory.remote.allowlisted-hosts}") String hosts,
        RemoteHttpClients.ServiceTokens credentials,ObjectMapper mapper) {
        return RemoteHttpClients.builder(transport("builder",endpoint,hosts,credentials,mapper));
    }
    @Bean Ports.EvaluationClient remoteEvaluator(
        @Value("${factory.remote.evaluation-uri}") URI endpoint,
        @Value("${factory.remote.allowlisted-hosts}") String hosts,
        RemoteHttpClients.ServiceTokens credentials,ObjectMapper mapper) {
        return RemoteHttpClients.evaluator(transport("evaluation",endpoint,hosts,credentials,mapper));
    }
    @Bean Ports.OptimizationClient remoteGepard(
        @Value("${factory.remote.optimizer-uri}") URI endpoint,
        @Value("${factory.remote.allowlisted-hosts}") String hosts,
        RemoteHttpClients.ServiceTokens credentials,ObjectMapper mapper) {
        return RemoteHttpClients.optimizer(transport("gepard",endpoint,hosts,credentials,mapper));
    }
    @Bean Ports.SoupClient disabledSoup() {
        return command -> { throw new IllegalStateException("SOUP_BACKEND_NOT_CONFIGURED"); };
    }
    @Bean OutboxDispatcher explicitCommandRelay(Ports.WorkflowLedger ledger,
        Ports.BuildClient builder,Ports.EvaluationClient evaluation,
        Ports.OptimizationClient optimization,Ports.SoupClient soup) {
        return new OutboxDispatcher(ledger,builder,evaluation,optimization,soup);
    }
    private static RemoteHttpClients.Transport transport(String service,URI endpoint,String configured,
        RemoteHttpClients.ServiceTokens credentials,ObjectMapper mapper) {
        Set<String> allowlist=Arrays.stream(configured.split(",")).map(String::trim)
            .filter(s -> !s.isEmpty()).collect(Collectors.toUnmodifiableSet());
        return new RemoteHttpClients.Transport(service,endpoint,allowlist,false,credentials,mapper);
    }
}
