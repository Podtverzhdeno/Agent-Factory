package com.agentfactory.control;

import java.lang.reflect.Proxy;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.concurrent.atomic.AtomicInteger;
import javax.sql.DataSource;

/** Dependency-free contract checks for the optional same-connection JDBC unit of work. */
public final class JdbcTransactionScopeTests {
    private JdbcTransactionScopeTests() { }

    private static final class Counters {
        final AtomicInteger commits = new AtomicInteger();
        final AtomicInteger rollbacks = new AtomicInteger();
        final AtomicInteger opened = new AtomicInteger();

        Connection connection() {
            opened.incrementAndGet();
            return (Connection) Proxy.newProxyInstance(Connection.class.getClassLoader(),
                new Class<?>[]{Connection.class}, (proxy, method, args) -> {
                    switch (method.getName()) {
                        case "setAutoCommit": return null;
                        case "commit": commits.incrementAndGet(); return null;
                        case "rollback": rollbacks.incrementAndGet(); return null;
                        case "close": return null;
                        case "getAutoCommit": return false;
                        default: throw new UnsupportedOperationException(method.getName());
                    }
                });
        }

        DataSource dataSource() {
            return (DataSource) Proxy.newProxyInstance(DataSource.class.getClassLoader(),
                new Class<?>[]{DataSource.class}, (proxy, method, args) -> {
                    if ("getConnection".equals(method.getName())) return connection();
                    throw new UnsupportedOperationException(method.getName());
                });
        }
    }

    private static void check(boolean ok) {
        if (!ok) throw new AssertionError("JDBC transaction invariant failed");
    }

    private static void rollbackOnly(JdbcTransactionScope scope, boolean sqlFailure) {
        try {
            scope.transaction(connection -> {
                try {
                    scope.transaction(nested -> {
                        check(connection == nested);
                        if (sqlFailure) throw new SQLException("nested SQL failure");
                        throw new IllegalArgumentException("nested domain failure");
                    });
                } catch (JdbcTransactionScope.PersistenceFailure | IllegalArgumentException expected) {
                    // Caller catching a nested failure must not permit outer commit.
                }
                return null;
            });
            throw new AssertionError("Expected rollback-only failure");
        } catch (IllegalStateException expected) {
            check("TRANSACTION_MARKED_ROLLBACK_ONLY".equals(expected.getMessage()));
        }
    }

    public static void main(String[] args) {
        Counters success = new Counters();
        JdbcTransactionScope unit = new JdbcTransactionScope(success.dataSource());
        check(unit.transaction(c -> unit.transaction(nested -> c == nested)));
        check(success.commits.get() == 1 && success.rollbacks.get() == 0
            && success.opened.get() == 1);

        Counters sql = new Counters();
        rollbackOnly(new JdbcTransactionScope(sql.dataSource()), true);
        check(sql.commits.get() == 0 && sql.rollbacks.get() == 1);

        Counters domain = new Counters();
        rollbackOnly(new JdbcTransactionScope(domain.dataSource()), false);
        check(domain.commits.get() == 0 && domain.rollbacks.get() == 1);

        System.out.println("JDBC TRANSACTION TESTS PASSED: 3");
    }
}
