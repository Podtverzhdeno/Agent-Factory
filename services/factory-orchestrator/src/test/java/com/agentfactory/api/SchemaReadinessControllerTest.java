package com.agentfactory.api;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.http.HttpStatus;

/** Fail-closed, read-only V1/V2 readiness and no diagnostics disclosure. */
final class SchemaReadinessControllerTest {
    @Test
    void missingDatasourceNeverCountsAsSchemaReady() {
        var factory=new StaticListableBeanFactory();
        var response=new SchemaReadinessController(factory.getBeanProvider(DataSource.class))
            .schema();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,response.getStatusCode());
        assertEquals("unavailable",response.getBody().get("schema"));
        assertEquals(1,response.getBody().size());
    }

    @Test
    void invalidConnectionIsClosedAndCannotCountAsSchemaReady() throws SQLException {
        var database=mock(DataSource.class);
        var connection=mock(Connection.class);
        when(database.getConnection()).thenReturn(connection);
        when(connection.isValid(2)).thenReturn(false);
        var factory=new StaticListableBeanFactory();
        factory.addBean("jdbc",database);
        var response=new SchemaReadinessController(factory.getBeanProvider(DataSource.class))
            .schema();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,response.getStatusCode());
        verify(connection).close();
        verify(connection,never()).createStatement();
    }

    @Test
    void missingMigrationIsMaskedAndClosesAllJdbcResources() throws SQLException {
        var database=mock(DataSource.class);
        var connection=mock(Connection.class);
        var statement=mock(Statement.class);
        when(database.getConnection()).thenReturn(connection);
        when(connection.isValid(2)).thenReturn(true);
        when(connection.createStatement()).thenReturn(statement);
        when(statement.executeQuery(anyString()))
            .thenThrow(new SQLException("sensitive_host:5432 secret table cp_event_inbox"));
        var factory=new StaticListableBeanFactory();
        factory.addBean("jdbc",database);
        var response=new SchemaReadinessController(factory.getBeanProvider(DataSource.class))
            .schema();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,response.getStatusCode());
        assertEquals("unavailable",response.getBody().get("schema"));
        assertFalse(response.toString().contains("sensitive_host"));
        assertFalse(response.toString().contains("cp_event_inbox"));
        verify(statement).close();
        verify(connection).close();
    }
}
