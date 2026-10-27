package com.agentfactory.registry;

import org.springframework.boot.jackson.autoconfigure.JsonMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.PropertyNamingStrategies;

/**
 * Strict Jackson 3 wire format. Domain objects never depend on Jackson.
 * Unexpected JSON fields are rejected rather than silently accepted.
 */
@Configuration(proxyBeanMethods = false)
public class RegistryJsonConfig {
    @Bean
    JsonMapperBuilderCustomizer registryJsonNaming() {
        return builder -> builder
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true);
    }
}
