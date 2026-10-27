package com.agentfactory.api;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.logging.Logger;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

/**
 * Isolated, opt-in trace-verification probe. Requests only local health routes.
 * Never sends JWT, tenant data, external business traffic or write requests.
 * Disabled outside smoke+jdbc POC and cannot make /readyz artificially green.
 */
@Configuration(proxyBeanMethods=false)
@Profile("railway-smoke & jdbc-poc")
@ConditionalOnProperty(prefix="factory.observability",name="self-probe-enabled",havingValue="true")
public class SmokeReadinessSelfProbe {
    private static final Logger LOGGER=Logger.getLogger(SmokeReadinessSelfProbe.class.getName());

    @Bean
    ApplicationRunner readOnlyTraceVerification(@Value("${server.port:8080}") int port) {
        return args -> Thread.ofVirtual().name("cp-readonly-observation-probe").start(() -> {
            try {
                // Allow Railway's dynamic OBI auto-instrumentation to attach.
                Thread.sleep(15000);
                boolean passed=checkLocalOnly(port);
                LOGGER.info("event=control_plane.observation outcome="
                    +(passed?"DATABASE_SCHEMA_PROBES_PASSED":"DATABASE_SCHEMA_PROBES_UNAVAILABLE"));
            } catch (InterruptedException cancelled) {
                Thread.currentThread().interrupt();
            }
        });
    }

    /** Invokes GET only, enforces loopback by construction, ignores response bodies. */
    static boolean checkLocalOnly(int port) {
        if(port<1 || port>65535) return false;
        try (HttpClient client=HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(2)).build()) {
            for(String endpoint:new String[]{"/persistencez","/schemaz"}) {
                HttpRequest request=HttpRequest.newBuilder(
                    URI.create("http://127.0.0.1:"+port+endpoint))
                    .GET().timeout(Duration.ofSeconds(3)).build();
                if(client.send(request,HttpResponse.BodyHandlers.discarding()).statusCode()!=200)
                    return false;
            }
            return true;
        } catch(java.io.IOException failure) {
            return false;
        } catch(InterruptedException cancelled) {
            Thread.currentThread().interrupt();
            return false;
        }
    }
}
