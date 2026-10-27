package com.agentfactory.registry;

import java.util.List;
import java.util.Map;
import static com.agentfactory.registry.ToolRegistry.*;

/** Pure recursive validation for the registry-owned subset of JSON object schemas. */
final class PayloadShapeValidator {
    private static final int MAX_DEPTH = 12;
    private static final int MAX_ITEMS = 512;
    private static final int MAX_STRING = 8_192;
    private PayloadShapeValidator() {}

    static void validate(Map<String, ?> payload, Shape shape) { validateObject(payload, shape, 0); }

    private static void validateObject(Map<String, ?> payload, Shape shape, int depth) {
        if (depth >= MAX_DEPTH || payload == null || payload.size() > MAX_ITEMS
            || !payload.keySet().containsAll(shape.required()))
            throw new RegistryFailure("PAYLOAD_SCHEMA_MISMATCH", "Invalid object depth, size or required fields");
        for (var field : payload.entrySet()) {
            FieldSpec spec = shape.fields().get(field.getKey());
            if (spec == null) throw new RegistryFailure("PAYLOAD_SCHEMA_MISMATCH", "Undeclared field");
            validateField(field.getValue(), spec, depth + 1);
        }
    }
    private static void validateField(Object value, FieldSpec spec, int depth) {
        if (value == null || depth >= MAX_DEPTH)
            throw new RegistryFailure("PAYLOAD_SCHEMA_MISMATCH", "Null or excessive nesting");
        boolean valid = switch (spec.type()) {
            case STRING -> value instanceof String x && x.length() <= MAX_STRING;
            case NUMBER -> value instanceof Number x && !(x instanceof Double d && !Double.isFinite(d))
                && !(x instanceof Float f && !Float.isFinite(f));
            case BOOLEAN -> value instanceof Boolean;
            case OBJECT -> value instanceof Map<?, ?>;
            case ARRAY -> value instanceof List<?>;
        };
        if (!valid) throw new RegistryFailure("PAYLOAD_SCHEMA_MISMATCH", "Incorrect field type");
        if (spec.type() == FieldType.OBJECT) {
            Map<?, ?> map = (Map<?, ?>) value;
            if (map.keySet().stream().anyMatch(k -> !(k instanceof String)))
                throw new RegistryFailure("PAYLOAD_SCHEMA_MISMATCH", "Object keys must be strings");
            @SuppressWarnings("unchecked") Map<String, ?> nested = (Map<String, ?>) map;
            validateObject(nested, spec.objectShape(), depth);
        } else if (spec.type() == FieldType.ARRAY) {
            List<?> items = (List<?>) value;
            if (items.size() > MAX_ITEMS)
                throw new RegistryFailure("PAYLOAD_SCHEMA_MISMATCH", "Array exceeds size limit");
            for (Object item : items) validateField(item, spec.arrayItem(), depth + 1);
        }
    }
}
