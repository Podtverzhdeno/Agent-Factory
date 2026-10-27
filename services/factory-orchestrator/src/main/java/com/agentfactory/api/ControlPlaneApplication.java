package com.agentfactory.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;

/**
 * Proposed API adapter only. Runtime ownership and deployable boundaries await ADR-0002.
 * Does not enable external Builder/Evaluator/Optimizer automatically.
 */
@SpringBootApplication(scanBasePackages = "com.agentfactory",
    exclude = DataSourceAutoConfiguration.class)
public class ControlPlaneApplication {
    public static void main(String[] args) {
        SpringApplication.run(ControlPlaneApplication.class, args);
    }
}
