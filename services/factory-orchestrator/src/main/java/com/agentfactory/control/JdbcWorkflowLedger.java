package com.agentfactory.control;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Optional;
import java.util.function.Function;

/**
 * Postgres transactional ledger PoC. The row includes inbox + command/notification outboxes;
 * all state transitions and outbox insertion commit atomically under SELECT FOR UPDATE.
 * The actual deployed data ownership is blocked by ADR-0002.
 */
public final class JdbcWorkflowLedger implements Ports.WorkflowLedger {
    public interface Codec {
        String encode(Workflow workflow);
        Workflow decode(String serialized);
    }
    private final JdbcTransactionScope transactions;
    private final Codec codec;
    public JdbcWorkflowLedger(JdbcTransactionScope transactions, Codec codec) {
        this.transactions=Objects.requireNonNull(transactions);
        this.codec=Objects.requireNonNull(codec);
    }
    private static void bind(PreparedStatement statement, String... values) throws SQLException {
        for(int i=0;i<values.length;i++) statement.setString(i+1,values[i]);
    }
    private static Workflow readOne(Connection c, String sql, Codec codec, String... values) throws SQLException {
        try(PreparedStatement statement=c.prepareStatement(sql)) {
            bind(statement,values);
            try(ResultSet result=statement.executeQuery()) {
                return result.next()?codec.decode(result.getString(1)):null;
            }
        }
    }
    private Workflow findById(Connection c,String tenant,String id,boolean lock) throws SQLException {
        Workflow workflow = readOne(c,"SELECT payload FROM cp_workflow WHERE tenant_id=? AND workflow_id=?"+
            (lock?" FOR UPDATE":""),codec,tenant,id);
        if (workflow != null && (!tenant.equals(workflow.tenantId) || !id.equals(workflow.workflowId))) {
            throw new IllegalStateException("STORED_WORKFLOW_IDENTITY_MISMATCH");
        }
        return workflow;
    }
    @Override public Workflow open(Workflow initial) {
        Objects.requireNonNull(initial);
        return transactions.transaction(c -> {
            try(PreparedStatement statement=c.prepareStatement(
                "INSERT INTO cp_workflow (tenant_id,workflow_id,idempotency_key,payload,action_pending,notification_pending,terminal,revision) "+
                "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING")) {
                statement.setString(1,initial.tenantId); statement.setString(2,initial.workflowId);
                statement.setString(3,initial.idempotencyKey); statement.setString(4,codec.encode(initial));
                statement.setBoolean(5,initial.hasPendingActions());
                statement.setBoolean(6,initial.publishedAuditCount<initial.audit.size());
                statement.setBoolean(7,terminal(initial.state)); statement.setLong(8,initial.revision);
                if(statement.executeUpdate()==1) return initial.copy();
            }
            Workflow existing=readOne(c,
                "SELECT payload FROM cp_workflow WHERE tenant_id=? AND idempotency_key=? FOR UPDATE",
                codec,initial.tenantId,initial.idempotencyKey);
            if(existing==null) throw new IllegalStateException("WORKFLOW_ALREADY_EXISTS");
            if(!existing.requestFingerprint.equals(initial.requestFingerprint))
                throw new IllegalStateException("IDEMPOTENCY_CONFLICT");
            return existing.copy();
        });
    }
    @Override public Optional<Workflow> byIdempotency(String tenant,String key) {
        return transactions.transaction(c -> {
            Workflow saved=readOne(c,"SELECT payload FROM cp_workflow WHERE tenant_id=? AND idempotency_key=?",
                codec,tenant,key);
            if(saved!=null && (!tenant.equals(saved.tenantId) || !key.equals(saved.idempotencyKey))) {
                throw new IllegalStateException("STORED_WORKFLOW_IDENTITY_MISMATCH");
            }
            return Optional.ofNullable(saved).map(Workflow::copy);
        });
    }
    @Override public Workflow get(String tenant,String workflow) {
        return transactions.transaction(c -> {
            Workflow found=findById(c,tenant,workflow,false);
            if(found==null) throw new NoSuchElementException("WORKFLOW_NOT_FOUND");
            return found.copy();
        });
    }
    @Override public <T> T transact(String tenant,String id,Function<Workflow,T> operation) {
        return transactions.transaction(c -> {
            Workflow stored=findById(c,tenant,id,true);
            if(stored==null) throw new NoSuchElementException("WORKFLOW_NOT_FOUND");
            Workflow working=stored.copy(); working.revision++;
            T result=operation.apply(working);
            if(stored.state!=working.state) working.audit.add(new Workflow.Audit(Instant.now(),
                stored.state,working.state,working.errorCode,working.correlationId));
            try(PreparedStatement statement=c.prepareStatement(
                "UPDATE cp_workflow SET payload=?,action_pending=?,notification_pending=?,terminal=?,revision=? "+
                "WHERE tenant_id=? AND workflow_id=? AND revision=?")) {
                statement.setString(1,codec.encode(working));
                statement.setBoolean(2,working.hasPendingActions());
                statement.setBoolean(3,working.publishedAuditCount<working.audit.size());
                statement.setBoolean(4,terminal(working.state));
                statement.setLong(5,working.revision);
                statement.setString(6,tenant);statement.setString(7,id);
                statement.setLong(8,stored.revision);
                if(statement.executeUpdate()!=1) throw new IllegalStateException("WORKFLOW_CONCURRENT_MODIFICATION");
            }
            return result;
        });
    }
    private static boolean terminal(Workflow.State state) {
        return state==Workflow.State.BLOCKED || state==Workflow.State.RELEASED ||
            state==Workflow.State.ROLLED_BACK;
    }
    private List<Ports.Key> keys(String sql) {
        return transactions.transaction(c -> {
            List<Ports.Key> keys=new ArrayList<>();
            try(PreparedStatement statement=c.prepareStatement(sql);
                ResultSet result=statement.executeQuery()) {
                while(result.next()) keys.add(new Ports.Key(result.getString(1),result.getString(2)));
            }
            return List.copyOf(keys);
        });
    }
    @Override public List<Ports.Key> activeKeys() {
        return keys("SELECT tenant_id,workflow_id FROM cp_workflow WHERE terminal=FALSE");
    }
    @Override public List<Ports.Key> withUndeliveredActions() {
        return keys("SELECT tenant_id,workflow_id FROM cp_workflow WHERE action_pending=TRUE AND terminal=FALSE");
    }
    @Override public List<Ports.Key> withUndeliveredEvents() {
        return keys("SELECT tenant_id,workflow_id FROM cp_workflow WHERE notification_pending=TRUE");
    }
}
