package com.agentfactory.control;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Objects;
import javax.sql.DataSource;

/**
 * One physical JDBC transaction for a workflow transition and local AgentStore write.
 * Experimental adapter, intentionally not enabled before ADR-0002 ratification.
 */
public final class JdbcTransactionScope {
    @FunctionalInterface public interface Work<T> { T apply(Connection connection) throws SQLException; }
    private final DataSource dataSource;
    private final ThreadLocal<Connection> current = new ThreadLocal<>();

    public JdbcTransactionScope(DataSource dataSource) { this.dataSource=Objects.requireNonNull(dataSource); }

    public <T> T transaction(Work<T> work) {
        Connection nested=current.get();
        if(nested!=null) {
            try { return work.apply(nested); }
            catch(SQLException ex) { throw new PersistenceFailure(ex); }
        }
        try(Connection connection=dataSource.getConnection()) {
            connection.setAutoCommit(false);
            current.set(connection);
            try {
                T result=work.apply(connection);
                connection.commit();
                return result;
            } catch(Throwable failure) {
                try { connection.rollback(); }
                catch(SQLException rollbackFailure) { failure.addSuppressed(rollbackFailure); }
                if(failure instanceof RuntimeException runtime) throw runtime;
                if(failure instanceof Error error) throw error;
                throw new PersistenceFailure((SQLException)failure);
            } finally {
                current.remove();
            }
        } catch(SQLException ex) { throw new PersistenceFailure(ex); }
    }

    public static final class PersistenceFailure extends RuntimeException {
        private static final long serialVersionUID=1L;
        public PersistenceFailure(SQLException cause) { super("PERSISTENCE_OPERATION_FAILED",cause); }
    }
}
