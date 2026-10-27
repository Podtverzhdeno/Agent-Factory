package com.agentfactory.registry;

import java.util.Locale;
import org.springframework.boot.jackson.autoconfigure.JsonFactoryBuilderCustomizer;
import org.springframework.boot.jackson.autoconfigure.JsonMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.core.JsonGenerator;
import tools.jackson.core.JsonParser;
import tools.jackson.core.StreamReadConstraints;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.databind.DeserializationContext;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.JacksonModule;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.SerializationContext;
import tools.jackson.databind.ValueDeserializer;
import tools.jackson.databind.ValueSerializer;
import tools.jackson.databind.module.SimpleModule;

import static com.agentfactory.registry.ToolRegistry.Effect;
import static com.agentfactory.registry.ToolRegistry.Risk;

/**
 * Strict Jackson 3 transport mapping, deliberately outside the pure-JDK domain.
 * Only risk and effect use lower-case v0 contract values; lifecycle/status/health
 * and denial enums remain upper-case as explicitly specified in OpenAPI.
 * Never change Enum.toString(): it participates in pinned manifest SHA-256 digests.
 */
@Configuration(proxyBeanMethods = false)
public class RegistryJsonConfig {
    @Bean
    JsonMapperBuilderCustomizer registryJsonNaming() {
        return builder -> builder
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true);
    }

    /** Parse-time protections apply before JSON reaches the domain validator. */
    @Bean
    JsonFactoryBuilderCustomizer registryJsonLimits() {
        return builder -> builder
            .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .streamReadConstraints(StreamReadConstraints.builder()
                .maxNestingDepth(16)
                .maxDocumentLength(1_048_576)
                .maxTokenCount(50_000)
                .maxStringLength(8_192)
                .maxNameLength(128)
                .maxNumberLength(64)
                .build());
    }

    @Bean
    JacksonModule registryWireEnums() {
        SimpleModule module = new SimpleModule("registry-v0-enums");
        module.addSerializer(Risk.class, lowerCaseSerializer());
        module.addSerializer(Effect.class, lowerCaseSerializer());
        module.addDeserializer(Risk.class, strictLowerCaseDeserializer(Risk.class));
        module.addDeserializer(Effect.class, strictLowerCaseDeserializer(Effect.class));
        return module;
    }

    private static <E extends Enum<E>> ValueSerializer<E> lowerCaseSerializer() {
        return new ValueSerializer<>() {
            @Override
            public void serialize(E value, JsonGenerator generator, SerializationContext context) {
                generator.writeString(value.name().toLowerCase(Locale.ROOT));
            }
        };
    }

    private static <E extends Enum<E>> ValueDeserializer<E> strictLowerCaseDeserializer(Class<E> enumType) {
        return new ValueDeserializer<>() {
            @Override
            public E deserialize(JsonParser parser, DeserializationContext context) {
                String value = parser.getValueAsString();
                if (value != null && value.equals(value.toLowerCase(Locale.ROOT))) {
                    try {
                        return Enum.valueOf(enumType, value.toUpperCase(Locale.ROOT));
                    } catch (IllegalArgumentException ignored) {
                        // Reject unknown values; never weaken to a default risk/effect.
                    }
                }
                throw new IllegalArgumentException("Unsupported lower-case " + enumType.getSimpleName() + " value");
            }
        };
    }
}
