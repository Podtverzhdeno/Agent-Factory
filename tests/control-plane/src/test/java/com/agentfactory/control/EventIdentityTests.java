package com.agentfactory.control;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** Verifies stable, content-addressed event identities without Jackson or Kafka. */
public final class EventIdentityTests {
    private EventIdentityTests() { }

    record Sample(String tenant, Map<String,String> tools, Set<String> scopes,
                  BigDecimal cost, Instant occurredAt) { }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] ignored) {
        var a=new LinkedHashMap<String,String>();
        a.put("tool-b","digest-b");
        a.put("tool-a","digest-a");
        var b=new LinkedHashMap<String,String>();
        b.put("tool-a","digest-a");
        b.put("tool-b","digest-b");
        Instant occurredAt=Instant.parse("2026-10-27T01:00:00Z");
        Sample first=new Sample("tenant-a",a,Set.of("read","audit"),
            new BigDecimal("1.00"),occurredAt);
        Sample equivalent=new Sample("tenant-a",b,Set.of("audit","read"),
            new BigDecimal("1.0"),occurredAt);
        String expected=EventIdentity.sha256(first);
        check(expected.equals(EventIdentity.sha256(equivalent)),
            "Order and BigDecimal scale must not change the semantic digest");
        check(expected.matches("[0-9a-f]{64}"),"Digest should be 256-bit hex");

        Sample differentTenant=new Sample("tenant-b",b,Set.of("audit","read"),
            new BigDecimal("1.0"),occurredAt);
        check(!expected.equals(EventIdentity.sha256(differentTenant)),
            "Tenant identity must be bound into event digest");

        Sample alteredTools=new Sample("tenant-a",Map.of("tool-a","digest-x","tool-b","digest-b"),
            Set.of("audit","read"),new BigDecimal("1.0"),occurredAt);
        check(!expected.equals(EventIdentity.sha256(alteredTools)),
            "Materially changed tool metadata must not deduplicate");

        check(!expected.equals(EventIdentity.sha256("tenant-a")),
            "Different payload types must have independent identities");
        System.out.println("EVENT IDENTITY TESTS PASSED: 4");
    }
}
