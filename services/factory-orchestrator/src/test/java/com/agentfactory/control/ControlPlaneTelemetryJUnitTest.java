package com.agentfactory.control;

import org.junit.jupiter.api.Test;

/** JUnit entry points for each independent pure-Java operational logging regression. */
final class ControlPlaneTelemetryJUnitTest {
    @Test void acknowledgedOutboxNeverLogsRawIds() {
        ControlPlaneTelemetryTests.logsAcceptedCommandWithoutRawIds();
    }
    @Test void diagnosticsOnlyAllowKnownCodesAndBoundAttempts() {
        ControlPlaneTelemetryTests.restrictsRemoteCodesAndCapsAttempts();
    }
    @Test void hashedReferencesAreStableButDoNotEmbedIds() {
        ControlPlaneTelemetryTests.saltedReferencesDoNotEmbedIdentifiers();
    }
    @Test void lifecycleEmitsOnlyAfterCommitAndDoesNotDuplicate() {
        ControlPlaneTelemetryTests.logsCommittedLifecycleNotificationsOnly();
    }
    @Test void publisherFailureIsSanitizedAndLeavesEventReplayable() {
        ControlPlaneTelemetryTests.failedPublisherIsLoggedButFailureRetainsReplay();
    }
    @Test void outboxAcceptanceLogFollowsDurableAck() {
        ControlPlaneTelemetryTests.dispatchOutcomesAreLoggedAfterLedgerCommit();
    }
}
