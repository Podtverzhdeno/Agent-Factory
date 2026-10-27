package com.agentfactory.registry;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;
import com.fasterxml.jackson.databind.module.SimpleModule;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.util.Locale;

import static com.agentfactory.registry.ToolRegistry.*;

/** Keep the domain independent of Jackson; apply the frozen v0 snake_case/lowercase JSON contract here. */
@Configuration
public class RegistryJsonConfig {
    @Bean Jackson2ObjectMapperBuilderCustomizer registryJsonNaming() {
        return builder -> {
            builder.propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
            builder.featuresToEnable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
        };
    }

    @Bean SimpleModule registryEnums() {
        SimpleModule module = new SimpleModule("registry-v0-enums");
        module.addSerializer(Effect.class, new LowercaseEnumSerializer<>());
        module.addSerializer(Risk.class, new LowercaseEnumSerializer<>());
        module.addDeserializer(Effect.class, new FlexibleEnumDeserializer<>(Effect.class));
        module.addDeserializer(Risk.class, new FlexibleEnumDeserializer<>(Risk.class));
        return module;
    }

    private static final class LowercaseEnumSerializer<T extends Enum<T>> extends JsonSerializer<T> {
        @Override public void serialize(T value, com.fasterxml.jackson.core.JsonGenerator out,
                                        SerializerProvider provider) throws IOException {
            out.writeString(value.name().toLowerCase(Locale.ROOT));
        }
    }
    private static final class FlexibleEnumDeserializer<T extends Enum<T>> extends StdDeserializer<T> {
        private final Class<T> enumType;
        private FlexibleEnumDeserializer(Class<T> enumType) {
            super(enumType);
            this.enumType = enumType;
        }
        @Override public T deserialize(JsonParser parser, com.fasterxml.jackson.databind.DeserializationContext context)
                throws IOException {
            String raw = parser.getValueAsString();
            if (raw == null) throw JsonMappingException.from(parser, "Expected enum string");
            try {
                return Enum.valueOf(enumType, raw.toUpperCase(Locale.ROOT));
            } catch (IllegalArgumentException error) {
                throw JsonMappingException.from(parser, "Unknown " + enumType.getSimpleName() + " value", error);
            }
        }
    }
}
