package com.agentfactory.api;

import com.agentfactory.control.InMemoryWorkflowLedger;
import com.agentfactory.control.JdbcAgentStore;
import com.agentfactory.control.JdbcTransactionScope;
import com.agentfactory.control.JdbcWorkflowLedger;
import com.agentfactory.control.OutboxDispatcher;
import com.agentfactory.control.Ports;
import com.agentfactory.store.AgentStore;
import com.agentfactory.store.InMemoryAgentStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.http.HttpStatus;
import org.springframework.mock.env.MockEnvironment;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/** Security and correctness gates for local, non-business readiness. */
final class RuntimeReadinessControllerTest {
    private record Adapters(JdbcWorkflowLedger ledger, JdbcAgentStore store) { }

    private static Adapters durable(DataSource source) {
        var tx=new JdbcTransactionScope(source);
        var codec=new JacksonStateCodec(new ObjectMapper().findAndRegisterModules());
        return new Adapters(new JdbcWorkflowLedger(tx,codec),new JdbcAgentStore(tx,codec));
    }

    private static OutboxDispatcher relay(Ports.WorkflowLedger ledger) {
        return new OutboxDispatcher(ledger,
            c -> new PortsReceipt().accept(c.operationId()),
            c -> new PortsReceipt().accept(c.operationId()),
            c -> new PortsReceipt().accept(c.operationId()),
            c -> new PortsReceipt().accept(c.operationId()));
    }

    private static final class PortsReceipt {
        com.agentfactory.control.Protocol.CommandReceipt accept(String operationId) {
            return new com.agentfactory.control.Protocol.CommandReceipt(operationId,true);
        }
    }

    private static RuntimeReadinessController controller(DataSource source,
        Ports.WorkflowLedger ledger,AgentStore store,OutboxDispatcher relay,
        String... profiles) {
        var beans=new StaticListableBeanFactory();
        if(source!=null) beans.addBean("jdbc",source);
        if(relay!=null) beans.addBean("outbox",relay);
        var env=new MockEnvironment();
        env.setActiveProfiles(profiles);
        return new RuntimeReadinessController(
            beans.getBeanProvider(DataSource.class),ledger,store,
            beans.getBeanProvider(OutboxDispatcher.class),env);
    }

    @Test void smokeProfileNeverClaimsReadyEvenWithJdbcAndRelay() throws SQLException {
        var ds=mock(DataSource.class);
        var a=durable(ds);
        var result=controller(ds,a.ledger(),a.store(),relay(a.ledger()),"railway-smoke","jdbc-poc").ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        verify(ds,never()).getConnection();
    }

    @Test void allVolatileAdaptersFailClosedWithoutTouchingDatabase() throws SQLException {
        var ds=mock(DataSource.class);
        var memory=new InMemoryWorkflowLedger();
        var result=controller(ds,memory,new InMemoryAgentStore(),relay(memory)).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        verify(ds,never()).getConnection();
    }

    @Test void durableLedgerWithVolatileRegistryIsNotReady() throws SQLException {
        var ds=mock(DataSource.class);
        var a=durable(ds);
        var result=controller(ds,a.ledger(),new InMemoryAgentStore(),relay(a.ledger())).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        verify(ds,never()).getConnection();
    }

    @Test void durableRegistryWithVolatileLedgerIsNotReady() throws SQLException {
        var ds=mock(DataSource.class);
        var a=durable(ds);
        var memory=new InMemoryWorkflowLedger();
        var result=controller(ds,memory,a.store(),relay(memory)).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        verify(ds,never()).getConnection();
    }

    @Test void remoteDispatchAbsentCannotClaimRuntimeReadiness() throws SQLException {
        var ds=mock(DataSource.class);
        var a=durable(ds);
        var result=controller(ds,a.ledger(),a.store(),null,"jdbc-poc").ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        verify(ds,never()).getConnection();
    }

    @Test void absentDataSourceFailsWithoutSensitiveDetails() {
        var mockSource=mock(DataSource.class);
        var a=durable(mockSource);
        var result=controller(null,a.ledger(),a.store(),relay(a.ledger())).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        assertEquals("unavailable",result.getBody().get("readiness"));
        assertEquals(1,result.getBody().size());
    }

    @Test void unavailableDatabaseMasksExceptionMessage() throws SQLException {
        var ds=mock(DataSource.class);
        when(ds.getConnection()).thenThrow(new SQLException("PASSWORD my-private-db.internal"));
        var a=durable(ds);
        var result=controller(ds,a.ledger(),a.store(),relay(a.ledger())).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        assertFalse(result.toString().contains("my-private-db"));
        assertFalse(result.toString().contains("PASSWORD"));
    }

    @Test void invalidConnectionClosesResourceWithoutSchemaReads() throws SQLException {
        var ds=mock(DataSource.class);
        var conn=mock(Connection.class);
        when(ds.getConnection()).thenReturn(conn);
        when(conn.isValid(2)).thenReturn(false);
        var a=durable(ds);
        var result=controller(ds,a.ledger(),a.store(),relay(a.ledger())).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        verify(conn,never()).createStatement();
        verify(conn).close();
    }

    @Test void migrationMissingFailsWithNoLeakedSqlOrDatabaseDetails() throws SQLException {
        var ds=mock(DataSource.class);
        var conn=mock(Connection.class);
        var stmt=mock(Statement.class);
        when(ds.getConnection()).thenReturn(conn);
        when(conn.isValid(2)).thenReturn(true);
        when(conn.createStatement()).thenReturn(stmt);
        when(stmt.executeQuery(anyString()))
            .thenThrow(new SQLException("private-db:5432 missing confidential tables"));
        var a=durable(ds);
        var result=controller(ds,a.ledger(),a.store(),relay(a.ledger())).ready();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,result.getStatusCode());
        assertFalse(result.toString().contains("private-db"));
        verify(stmt).close();
        verify(conn).close();
    }

    @Test void durableAdaptersRelayAndAllSchemaQueriesPassLocalReadiness() throws SQLException {
        var ds=mock(DataSource.class);
        var conn=mock(Connection.class);
        var stmt=mock(Statement.class);
        var results=mock(ResultSet.class);
        when(ds.getConnection()).thenReturn(conn);
        when(conn.isValid(2)).thenReturn(true);
        when(conn.createStatement()).thenReturn(stmt);
        when(stmt.executeQuery(anyString())).thenReturn(results);
        var a=durable(ds);
        var response=controller(ds,a.ledger(),a.store(),relay(a.ledger()),"jdbc-poc","remote-poc").ready();
        assertEquals(HttpStatus.OK,response.getStatusCode());
        assertEquals("local-checks-passed",response.getBody().get("readiness"));
        assertEquals(1,response.getBody().size());
        verify(stmt,times(6)).executeQuery(anyString());
        verify(results,atLeastOnce()).close();
        verify(stmt).close();
        verify(conn).close();
    }
}
