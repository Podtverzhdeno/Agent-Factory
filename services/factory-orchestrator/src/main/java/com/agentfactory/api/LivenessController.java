package com.agentfactory.api;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Process liveness only. A 200 response does NOT attest database availability,
 * verified evaluation evidence, registered external APIs, or production readiness.
 */
@RestController
public final class LivenessController {
    @GetMapping("/healthz")
    public Map<String,String> healthy() {
        return Map.of("status","alive");
    }
}
