package com.agentfactory.api;

import com.agentfactory.control.InMemoryWorkflowLedger;
import com.agentfactory.control.JdbcAgentStore;
import com.agentfactory.control.JdbcTransactionScope;
import com.agentfactory.control.JdbcWorkflowLedger;
import com.agentfactory.control.Ports;
import com.agentfactory.control.Protocol;
import com.agentfactory.store.AgentStore;
import com.agentfactory.store.InMemoryAgentStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * A remote adapter can generate irreversible third-party effects; durable
 * ledger + durable registry are required *before* its dispatcher may boot.
 */
final class RemoteProofOfConceptConfigurationTest {
    private final RemoteProofOfConceptConfiguration config =
        new RemoteProofOfConceptConfiguration();

    private static Ports.BuildClient build() {
        return c -> new Protocol.CommandReceipt(c.operationId(),true);
    }

    private static Ports.EvaluationClient evaluation() {
        return c -> new Protocol.CommandReceipt(c.operationId(),true);
    }

    private static Ports.OptimizationClient optimization() {
        return c -> new Protocol.CommandReceipt(c.operationId(),true);
    }

    private static Ports.SoupClient soup() {
        return c -> new Protocol.CommandReceipt(c.operationId(),true);
    }

    private static JdbcTransactionScope transactions() {
        return new JdbcTransactionScope(mock(DataSource.class));
    }

    private static JacksonStateCodec codec() {
        return new JacksonStateCodec(new ObjectMapper().findAndRegisterModules());
    }

    private void rejects(Ports.WorkflowLedger ledger, AgentStore store) {
        var error=assertThrows(IllegalStateException.class,
            () -> config.explicitCommandRelay(ledger,store,build(),evaluation(),optimization(),soup()));
        assertEquals("REMOTE_REQUIRES_DURABLE_POSTGRESQL",error.getMessage());
    }

    @Test void memoryOnlyRuntimeCannotEnableOutboundSideEffects() {
        rejects(new InMemoryWorkflowLedger(),new InMemoryAgentStore());
    }

    @Test void jdbcWorkflowAloneDoesNotMakeRemoteSideEffectsDurable() {
        rejects(new JdbcWorkflowLedger(transactions(),codec()),new InMemoryAgentStore());
    }

    @Test void jdbcAgentStoreAloneDoesNotMakeRemoteSideEffectsDurable() {
        rejects(new InMemoryWorkflowLedger(),new JdbcAgentStore(transactions(),codec()));
    }

    @Test void bothJdbcAdaptersPermitRelayConstructionWithoutSendingNetworkCalls() {
        var shared=transactions();
        var relay=config.explicitCommandRelay(
            new JdbcWorkflowLedger(shared,codec()),
            new JdbcAgentStore(shared,codec()),
            build(),evaluation(),optimization(),soup());
        assertNotNull(relay);
    }
}
