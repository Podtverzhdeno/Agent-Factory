package com.agentfactory.api;

import com.agentfactory.control.ControlPlaneComponentTests;
import com.agentfactory.control.JdbcTransactionScopeTests;
import org.junit.jupiter.api.Test;

/**
 * Runs the exact dependency-free acceptance suite in Maven/Surefire.
 * The standalone javac entry point remains usable without Spring dependencies.
 */
final class ControlPlaneComponentSuiteTest {
    @Test
    void componentScenariosMustPassBeforeMavenBuildSucceeds() {
        ControlPlaneComponentTests.main(new String[0]);
    }

    @Test
    void nestedJdbcFailuresMustRollBack() {
        JdbcTransactionScopeTests.main(new String[0]);
    }
}
