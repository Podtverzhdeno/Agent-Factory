package com.agentfactory.api;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** Liveness only. A 200 response is NOT proof of ready upstream integrations. */
@RestController
public class ControlPlaneHealthController {
    @GetMapping("/healthz")
    public Map<String, String> liveness() {
        return Map.of("status", "BOOTED");
    }
}
