package com.agentfactory.api;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.sql.Connection;
import java.sql.SQLException;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.http.HttpStatus;

/** Fail-closed tests: no credentials, JDBC URL, or internal exception is exposed. */
final class PersistenceProbeControllerTest {
    @Test
    void absentJdbcConnectionCannotBeReportedAsReady() {
        var factory=new StaticListableBeanFactory();
        var response=new PersistenceProbeController(factory.getBeanProvider(DataSource.class))
            .persistence();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,response.getStatusCode());
        assertEquals("unavailable",response.getBody().get("persistence"));
        assertEquals(1,response.getBody().size());
    }

    @Test
    void jdbcConnectionErrorIsMaskedAndReturns503() throws SQLException {
        var database=mock(DataSource.class);
        when(database.getConnection()).thenThrow(new SQLException("private-jdbc-host:5432"));
        var factory=new StaticListableBeanFactory();
        factory.addBean("jdbc",database);
        var response=new PersistenceProbeController(factory.getBeanProvider(DataSource.class))
            .persistence();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,response.getStatusCode());
        assertEquals("unavailable",response.getBody().get("persistence"));
        assertFalse(response.toString().contains("private-jdbc-host"));
        verify(database,times(1)).getConnection();
    }

    @Test
    void invalidConnectionIsClosedAndReturns503() throws SQLException {
        var database=mock(DataSource.class);
        var connection=mock(Connection.class);
        when(database.getConnection()).thenReturn(connection);
        when(connection.isValid(2)).thenReturn(false);
        var factory=new StaticListableBeanFactory();
        factory.addBean("jdbc",database);
        var response=new PersistenceProbeController(factory.getBeanProvider(DataSource.class))
            .persistence();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,response.getStatusCode());
        verify(connection).close();
    }
}
