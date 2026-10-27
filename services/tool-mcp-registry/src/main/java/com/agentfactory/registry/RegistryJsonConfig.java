package com.agentfactory.registry;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Honor snake_case transport contract from docs/parallel/CONTRACTS_V0.md. */
@Configuration
public class RegistryJsonConfig {
    @Bean Jackson2ObjectMapperBuilderCustomizer registryJsonNaming() {
        return builder -> builder.propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    }
}
