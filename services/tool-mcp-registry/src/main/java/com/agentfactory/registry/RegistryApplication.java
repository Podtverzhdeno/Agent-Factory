package com.agentfactory.registry;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.util.Map;
import java.util.Set;

/**
 * Contract adapter only. Default startup supplies no independently attested schema
 * or MCP endpoint trust roots. Synthetic fixtures must be injected by tests.
 * Operator trust provisioning and deployment await owner-ratified ADR-0002.
 */
@SpringBootApplication
public class RegistryApplication {
    public static void main(String[] args) {
        SpringApplication.run(RegistryApplication.class, args);
    }

    @Bean
    ToolRegistry registry() {
        return new ToolRegistry(Map.of(), Set.of());
    }
}
