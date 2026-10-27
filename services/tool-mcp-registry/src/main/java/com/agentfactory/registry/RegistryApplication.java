package com.agentfactory.registry;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.util.Map;
import java.util.Set;

import static com.agentfactory.registry.ToolRegistry.*;

/** Contract adapter only. Synthetic endpoint references never resolve to live MCP connections. */
@SpringBootApplication
public class RegistryApplication {
    public static void main(String[] args) { SpringApplication.run(RegistryApplication.class, args); }

    @Bean
    ToolRegistry registry() {
        // These are sample shape definitions and non-resolvable fixture refs, not automatically approved tools.
        return new ToolRegistry(Map.of(
            "artifact://schemas/file-input", new Shape(Map.of("file", FieldSpec.scalar(FieldType.STRING)), Set.of("file"), false),
            "artifact://schemas/rows", new Shape(Map.of("rows", FieldSpec.array(FieldSpec.object(new Shape(Map.of("sku", FieldSpec.scalar(FieldType.STRING), "quantity", FieldSpec.scalar(FieldType.NUMBER)), Set.of("sku","quantity"), false)))), Set.of("rows"), false),
            "artifact://schemas/lookup-input", new Shape(Map.of("sku", FieldSpec.scalar(FieldType.STRING)), Set.of("sku"), false),
            "artifact://schemas/lookup-output", new Shape(Map.of("items", FieldSpec.array(FieldSpec.object(new Shape(Map.of("sku", FieldSpec.scalar(FieldType.STRING), "price", FieldSpec.scalar(FieldType.NUMBER)), Set.of("sku","price"), false)))), Set.of("items"), false),
            "artifact://schemas/write-input", new Shape(Map.of("rows", FieldSpec.array(FieldSpec.object(new Shape(Map.of("sku", FieldSpec.scalar(FieldType.STRING), "quantity", FieldSpec.scalar(FieldType.NUMBER)), Set.of("sku","quantity"), false)))), Set.of("rows"), false),
            "artifact://schemas/file-output", new Shape(Map.of("draft_file_ref", FieldSpec.scalar(FieldType.STRING)), Set.of("draft_file_ref"), false)
        ), Set.of("artifact://approved/endpoints/xlsx", "artifact://approved/endpoints/catalog"));
    }
}
