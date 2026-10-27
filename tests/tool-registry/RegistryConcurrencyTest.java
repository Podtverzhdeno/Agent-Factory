package com.agentfactory.registry;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static com.agentfactory.registry.ToolRegistry.*;
import static com.agentfactory.registry.RegistrySelfTest.*;

/** Deterministic barrier-driven checks of single-instance transactional operations. */
public final class RegistryConcurrencyTest {
    private RegistryConcurrencyTest() {}

    public static void main(String[] args) throws Exception {
        ToolRegistry registry = fixture();
        Manifest read = manifest("shared.concurrent", "1.0.0", "read_xlsx", FILE_IN, ROWS,
            XLSX_ENDPOINT, Set.of(Effect.READ), Set.of("xlsx:read"), Risk.LOW);
        int actors = 24;
        CountDownLatch ready = new CountDownLatch(actors);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<String>> results = new ArrayList<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(actors)) {
            for (int i = 0; i < actors; i++) {
                results.add(pool.submit(new Callable<>() {
                    @Override public String call() throws Exception {
                        ready.countDown();
                        if (!start.await(10, TimeUnit.SECONDS)) throw new AssertionError("Timed out waiting for release");
                        try {
                            registry.registerDraft(author, read);
                            return "REGISTERED";
                        } catch (RegistryFailure failure) {
                            return failure.code;
                        }
                    }
                }));
            }
            if (!ready.await(10, TimeUnit.SECONDS)) throw new AssertionError("Threads not ready");
            start.countDown();
            int accepted = 0;
            for (Future<String> future : results) {
                String result = future.get(10, TimeUnit.SECONDS);
                if (result.equals("REGISTERED")) accepted++;
                else if (!result.equals("VERSION_EXISTS")) throw new AssertionError("Unexpected error: " + result);
            }
            if (accepted != 1) throw new AssertionError("Exactly one immutable registration expected; actual=" + accepted);
        }
        assertSingleSuccessfulTransition(24, () -> {
            registry.approve(reviewer, "shared.concurrent", "1.0.0", "execute");
        }, "IMMUTABLE", "approval");
        Caller auditor = new Caller("audit", "tenant-a", Set.of("registry:audit"));
        if (registry.auditTrail(auditor).size() != 2) throw new AssertionError("Audit must not contain duplicate transitions");
        if (registry.select(user, task("read_xlsx")).selectedTools().size() != 1)
            throw new AssertionError("Approved operation missing after concurrent registration");
        // Snapshot responses and immutable event records may be safely consumed across threads.
        List<Selection> copies = new ArrayList<>();
        for (int i = 0; i < 10; i++) copies.add(registry.select(user, task("read_xlsx")));
        String revision = copies.getFirst().registryRevision();
        if (copies.stream().anyMatch(s -> !s.registryRevision().equals(revision)))
            throw new AssertionError("Same registry state produced differing revisions");
        assertSingleSuccessfulTransition(24, () -> {
            registry.revoke(reviewer, "shared.concurrent", "1.0.0", "execute");
        }, "INVALID_STATE", "revocation");
        if (registry.auditTrail(auditor).size() != 3 || registry.select(user, task("read_xlsx")).decision() != Decision.BLOCKED)
            throw new AssertionError("Revocation must be atomic and audited");
        System.out.println("PASS: 24-way concurrent registration, approval and revocation linearize exactly once");
    }

    @FunctionalInterface
    private interface Transition { void run(); }

    /** Independent barrier-controlled actor races must emit precisely one success and audit event. */
    private static void assertSingleSuccessfulTransition(int actors, Transition action,
                                                          String expectedFailure, String transition) throws Exception {
        CountDownLatch ready = new CountDownLatch(actors);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<String>> outcomes = new ArrayList<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(actors)) {
            for (int i = 0; i < actors; i++) {
                outcomes.add(pool.submit(() -> {
                    ready.countDown();
                    if (!start.await(10, TimeUnit.SECONDS)) throw new AssertionError("Barrier timeout");
                    try {
                        action.run();
                        return "SUCCESS";
                    } catch (RegistryFailure error) {
                        return error.code;
                    }
                }));
            }
            if (!ready.await(10, TimeUnit.SECONDS)) throw new AssertionError("Actors not ready");
            start.countDown();
            int succeeded = 0;
            for (Future<String> outcome : outcomes) {
                String value = outcome.get(10, TimeUnit.SECONDS);
                if ("SUCCESS".equals(value)) succeeded++;
                else if (!expectedFailure.equals(value)) {
                    throw new AssertionError("Unexpected " + transition + " error: " + value);
                }
            }
            if (succeeded != 1) {
                throw new AssertionError("Expected one " + transition + ", got " + succeeded);
            }
        }
    }
}
