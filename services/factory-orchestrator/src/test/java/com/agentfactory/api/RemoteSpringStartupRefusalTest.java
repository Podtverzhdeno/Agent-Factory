package com.agentfactory.api;

import org.junit.jupiter.api.Test;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Real Spring startup must reject external side-effect wiring if the JDBC
 * profile is missing. Tests with synthetic credentials and unusable HTTPS
 * destinations; no outbound network requests are made.
 */
final class RemoteSpringStartupRefusalTest {
    @Configuration(proxyBeanMethods = false)
    static class SyntheticServiceCredentials {
        @Bean RemoteHttpClients.ServiceTokens isolatedServiceTokens() {
            return (service, tenant) -> "synthetic-test-token";
        }
    }

    @Test
    void completeSpringBootApplicationRefusesRemoteWithoutJdbcEvenWithCredentials() {
        RuntimeException error=assertThrows(RuntimeException.class, () -> {
            try (ConfigurableApplicationContext application =
                new SpringApplicationBuilder(ControlPlaneApplication.class,
                    SyntheticServiceCredentials.class)
                    .web(WebApplicationType.SERVLET)
                    .profiles("railway-smoke","remote-poc")
                    .properties(
                        "server.port=0",
                        "spring.main.banner-mode=off",
                        "factory.remote.enabled=true",
                        "factory.remote.builder-uri=https://builder.example.invalid",
                        "factory.remote.evaluation-uri=https://evaluation.example.invalid",
                        "factory.remote.optimizer-uri=https://optimizer.example.invalid",
                        "factory.remote.allowlisted-hosts=builder.example.invalid,evaluation.example.invalid,optimizer.example.invalid"
                    ).run()) {
                fail("Remote HTTP configuration unexpectedly started without PostgreSQL");
            }
        });
        boolean refused=false;
        for(Throwable cause=error;cause!=null;cause=cause.getCause()) {
            if(cause.getMessage()!=null &&
                cause.getMessage().contains("REMOTE_REQUIRES_DURABLE_POSTGRESQL")) {
                refused=true;
                break;
            }
        }
        assertTrue(refused, "Application must fail because remote-poc requires durable PostgreSQL");
    }
}
