package com.agentfactory.control;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.RecordComponent;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

/** Canonical event identity across JVM restarts and JSON persistence. Never use toString() for deduplication. */
public final class EventIdentity {
    private EventIdentity() { }

    public static String sha256(Object value) {
        try {
            var bytes = new ByteArrayOutputStream();
            var output = new DataOutputStream(bytes);
            write(output, value);
            output.flush();
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes.toByteArray()));
        } catch (IOException | NoSuchAlgorithmException e) {
            throw new IllegalStateException("EVENT_FINGERPRINT_FAILED", e);
        }
    }

    private static void write(DataOutputStream out, Object value) throws IOException {
        if (value == null) { out.writeByte(0); return; }
        if (value instanceof String s) { out.writeByte(1); writeUtf8(out,s); return; }
        if (value instanceof Boolean b) { out.writeByte(2); out.writeBoolean(b); return; }
        if (value instanceof BigDecimal d) { out.writeByte(3); writeUtf8(out,d.stripTrailingZeros().toPlainString()); return; }
        if (value instanceof Number n) { out.writeByte(4); writeUtf8(out,n.toString()); return; }
        if (value instanceof Instant i) { out.writeByte(5); out.writeLong(i.getEpochSecond()); out.writeInt(i.getNano()); return; }
        if (value instanceof Enum<?> e) { out.writeByte(6); writeUtf8(out,e.getDeclaringClass().getName()); writeUtf8(out,e.name()); return; }
        if (value instanceof Map<?,?> map) {
            out.writeByte(7); out.writeInt(map.size());
            var entries = new ArrayList<Map.Entry<?,?>>(map.entrySet());
            entries.sort(Comparator.comparing(entry -> String.valueOf(entry.getKey())));
            for (var entry : entries) { write(out,entry.getKey()); write(out,entry.getValue()); }
            return;
        }
        if (value instanceof Collection<?> elements) {
            out.writeByte(8); out.writeInt(elements.size());
            if (value instanceof java.util.Set<?>) {
                List<byte[]> encoded = new ArrayList<>();
                for (Object element : elements) {
                    var buffer = new ByteArrayOutputStream();
                    write(new DataOutputStream(buffer),element);
                    encoded.add(buffer.toByteArray());
                }
                encoded.sort((a,b) -> java.util.Arrays.compareUnsigned(a,b));
                for (byte[] encodedElement : encoded) { out.writeInt(encodedElement.length); out.write(encodedElement); }
            } else {
                for (Object element : elements) write(out,element);
            }
            return;
        }
        if (value.getClass().isRecord()) {
            out.writeByte(9); writeUtf8(out,value.getClass().getName());
            RecordComponent[] components = value.getClass().getRecordComponents();
            out.writeInt(components.length);
            try {
                for (RecordComponent component : components) {
                    writeUtf8(out,component.getName());
                    write(out,component.getAccessor().invoke(value));
                }
            } catch (IllegalAccessException | InvocationTargetException e) {
                throw new IllegalStateException("EVENT_FINGERPRINT_FAILED",e);
            }
            return;
        }
        throw new IllegalArgumentException("UNSUPPORTED_EVENT_PAYLOAD_TYPE: " + value.getClass().getName());
    }
    private static void writeUtf8(DataOutputStream out,String value) throws IOException {
        byte[] bytes=value.getBytes(StandardCharsets.UTF_8);
        out.writeInt(bytes.length); out.write(bytes);
    }
}
