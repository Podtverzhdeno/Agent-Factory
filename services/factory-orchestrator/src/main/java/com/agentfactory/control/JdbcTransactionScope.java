package com.agentfactory.control;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Objects;
import javax.sql.DataSource;

/**
 * Optional candidate implementation. All participating repositories must share this
 * instance to enlist in the same physical transaction. Not activated until ADR-0002.
 */
public final class JdbcTransactionScope {
    @FunctionalInterface
    public interface Work<T> {
        T apply(Connection connection) throws SQLException;
    }

    private static final class Context {
        final Connection connection;
        boolean rollbackOnly;

        Context(Connection connection) {
            this.connection = connection;
        }
    }

    private final DataSource dataSource;
    private final ThreadLocal<Context> context = new ThreadLocal<>();

    public JdbcTransactionScope(DataSource dataSource) {
        this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
    }

    public <T> T transaction(Work<T> work) {
        Objects.requireNonNull(work, "work");
        Context nested = context.get();
        if (nested != null) {
            try {
                return work.apply(nested.connection);
            } catch (SQLException error) {
                nested.rollbackOnly = true;
                throw new PersistenceFailure(error);
            } catch (RuntimeException | Error error) {
                nested.rollbackOnly = true;
                throw error;
            }
        }

        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            Context current = new Context(connection);
            context.set(current);
            try {
                T result = work.apply(connection);
                if (current.rollbackOnly) {
                    throw new IllegalStateException("TRANSACTION_MARKED_ROLLBACK_ONLY");
                }
                connection.commit();
                return result;
            } catch (SQLException error) {
                rollback(connection, error);
                throw new PersistenceFailure(error);
            } catch (RuntimeException | Error error) {
                rollback(connection, error);
                throw error;
            } finally {
                context.remove();
            }
        } catch (SQLException error) {
            throw new PersistenceFailure(error);
        }
    }

    private static void rollback(Connection connection, Throwable original) {
        try {
            connection.rollback();
        } catch (SQLException rollbackError) {
            original.addSuppressed(rollbackError);
        }
    }

    public static final class PersistenceFailure extends RuntimeException {
        private static final long serialVersionUID = 1L;
        public PersistenceFailure(SQLException cause) {
            super("PERSISTENCE_OPERATION_FAILED", cause);
        }
    }
}
