package com.agentfactory.control;

import com.agentfactory.store.AgentStore;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * Candidate PostgreSQL AgentStore adapter, not enabled until the owner ratifies ADR-0002.
 * Uses the exact same JDBC transaction as JdbcWorkflowLedger: candidate creation/release
 * and workflow state either commit together or roll back together.
 */
public final class JdbcAgentStore implements AgentStore {
    public interface Codec {
        String write(Object record);
        <T> T read(String json, Class<T> recordType);
    }
    private final JdbcTransactionScope tx;
    private final Codec codec;
    public JdbcAgentStore(JdbcTransactionScope transactions, Codec codec) {
        this.tx=Objects.requireNonNull(transactions);this.codec=Objects.requireNonNull(codec);
    }
    private static void require(boolean ok,String message) {
        if(!ok) throw new IllegalStateException(message);
    }
    private static void bind(PreparedStatement statement,String... values) throws SQLException {
        for(int i=0;i<values.length;i++) statement.setString(i+1,values[i]);
    }
    private void lock(Connection c,String tenant,String agent) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "INSERT INTO cp_agent_lock(tenant_id,agent_id) VALUES(?,?) ON CONFLICT DO NOTHING")) {
            bind(st,tenant,agent);st.executeUpdate();
        }
        try(PreparedStatement st=c.prepareStatement(
            "SELECT agent_id FROM cp_agent_lock WHERE tenant_id=? AND agent_id=? FOR UPDATE")) {
            bind(st,tenant,agent);
            try(ResultSet rs=st.executeQuery()){require(rs.next(),"AGENT_LOCK_FAILED");}
        }
    }
    private record Operation(String fingerprint,String result) { }
    private Operation operation(Connection c,String tenant,String kind,String key) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "SELECT fingerprint,result_json FROM cp_agent_operation WHERE tenant_id=? AND operation_kind=? AND idempotency_key=?")) {
            bind(st,tenant,kind,key);
            try(ResultSet rs=st.executeQuery()) {
                return rs.next()?new Operation(rs.getString(1),rs.getString(2)):null;
            }
        }
    }
    private void recordOperation(Connection c,String tenant,String kind,String key,
                                 String fingerprint,Object result) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "INSERT INTO cp_agent_operation(tenant_id,operation_kind,idempotency_key,fingerprint,result_json) VALUES(?,?,?,?,?)")) {
            bind(st,tenant,kind,key,fingerprint,codec.write(result));st.executeUpdate();
        }
    }
    private Version version(Connection c,String tenant,String agent,long n) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "SELECT payload FROM cp_agent_version WHERE tenant_id=? AND agent_id=? AND version=?")) {
            st.setString(1,tenant);st.setString(2,agent);st.setLong(3,n);
            try(ResultSet rs=st.executeQuery()) {
                return rs.next()?codec.read(rs.getString(1),Version.class):null;
            }
        }
    }
    private List<Version> versions(Connection c,String tenant,String agent) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "SELECT payload FROM cp_agent_version WHERE tenant_id=? AND agent_id=? ORDER BY version")) {
            bind(st,tenant,agent);
            List<Version> result=new ArrayList<>();
            try(ResultSet rs=st.executeQuery()) {
                while(rs.next()) result.add(codec.read(rs.getString(1),Version.class));
            }
            return List.copyOf(result);
        }
    }
    private void insertVersion(Connection c,Version version) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "INSERT INTO cp_agent_version(tenant_id,agent_id,version,payload) VALUES(?,?,?,?)")) {
            st.setString(1,version.tenantId());st.setString(2,version.agentId());
            st.setLong(3,version.version());st.setString(4,codec.write(version));st.executeUpdate();
        }
    }
    private void updateVersion(Connection c,Version version) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "UPDATE cp_agent_version SET payload=? WHERE tenant_id=? AND agent_id=? AND version=?")) {
            st.setString(1,codec.write(version));st.setString(2,version.tenantId());
            st.setString(3,version.agentId());st.setLong(4,version.version());
            require(st.executeUpdate()==1,"VERSION_NOT_FOUND");
        }
    }
    private void transition(Connection c,String tenant,String agent,long n,Channel from,
                            Channel to,String operation,String evaluation,Set<String> approvals) throws SQLException {
        try(PreparedStatement st=c.prepareStatement(
            "INSERT INTO cp_agent_transition(tenant_id,agent_id,payload) VALUES(?,?,?)")) {
            bind(st,tenant,agent,codec.write(new Transition(n,from,to,operation,evaluation,approvals)));
            st.executeUpdate();
        }
    }
    private Optional<Version> active(Connection c,String tenant,String agent) throws SQLException {
        return versions(c,tenant,agent).stream().filter(v -> v.channel()==Channel.RELEASED).findFirst();
    }
    @Override public Version registerCandidate(Metadata m,String key) {
        Objects.requireNonNull(m); Objects.requireNonNull(key);
        return tx.transaction(c -> {
            lock(c,m.tenantId(),m.agentId());
            String fingerprint=EventIdentity.sha256(m);
            Operation prior=operation(c,m.tenantId(),"candidate",key);
            if(prior!=null) {
                require(prior.fingerprint().equals(fingerprint),"IDEMPOTENCY_CONFLICT");
                return codec.read(prior.result(),Version.class);
            }
            require(m.evidence()!=null && m.evidence().complete(),"INCOMPLETE_EVIDENCE");
            require(m.specDigest().equals(m.evidence().specDigest()),"SPEC_DIGEST_MISMATCH");
            List<Version> old=versions(c,m.tenantId(),m.agentId());
            Version candidate=new Version(m.tenantId(),m.agentId(),old.size()+1L,
                m.specRef(),m.specDigest(),m.toolDigests(),m.modelRouteDigest(),
                m.a2aCardRef(),null,m.evidence(),Channel.VERIFIED);
            insertVersion(c,candidate);
            transition(c,m.tenantId(),m.agentId(),candidate.version(),Channel.CANDIDATE,
                Channel.VERIFIED,key,m.evidence().evaluationRunId(),Set.of());
            recordOperation(c,m.tenantId(),"candidate",key,fingerprint,candidate);
            return candidate;
        });
    }
    @Override public Version promote(String tenant,String agent,long n,String key,Set<String> approvals,boolean auto) {
        Objects.requireNonNull(approvals); Objects.requireNonNull(key);
        return tx.transaction(c -> {
            lock(c,tenant,agent);
            String fingerprint=EventIdentity.sha256(List.of(agent,n,auto,Set.copyOf(approvals)));
            Operation prior=operation(c,tenant,"promote",key);
            if(prior!=null) {
                require(prior.fingerprint().equals(fingerprint),"IDEMPOTENCY_CONFLICT");
                return codec.read(prior.result(),Version.class);
            }
            Version candidate=version(c,tenant,agent,n);
            require(candidate!=null,"VERSION_NOT_FOUND");
            require(candidate.channel()==Channel.VERIFIED && candidate.evidence().complete(),"QUALITY_GATE_BLOCKED");
            require(auto ? (candidate.evidence().risk()==Risk.LOW && approvals.isEmpty())
                : approvals.contains("release:approve"),"HUMAN_APPROVAL_REQUIRED");
            Optional<Version> current=active(c,tenant,agent);
            String rollbackRef=null;
            if(current.isPresent()) {
                Version previous=current.orElseThrow();
                rollbackRef="agentstore://"+tenant+"/"+agent+"/"+previous.version();
                updateVersion(c,previous.withChannel(Channel.VERIFIED));
                transition(c,tenant,agent,previous.version(),Channel.RELEASED,Channel.VERIFIED,
                    key,previous.evidence().evaluationRunId(),Set.of());
            }
            Version released=new Version(candidate.tenantId(),candidate.agentId(),candidate.version(),
                candidate.specRef(),candidate.specDigest(),candidate.toolDigests(),
                candidate.modelRouteDigest(),candidate.a2aCardRef(),rollbackRef,
                candidate.evidence(),Channel.RELEASED);
            updateVersion(c,released);
            transition(c,tenant,agent,n,Channel.VERIFIED,Channel.RELEASED,key,
                candidate.evidence().evaluationRunId(),approvals);
            recordOperation(c,tenant,"promote",key,fingerprint,released);
            return released;
        });
    }
    public record RollbackResult(String digest,Version restoredSnapshot) { }
    @Override public Rollback rollback(String tenant,String agent,long n,String key) {
        Objects.requireNonNull(key);
        return tx.transaction(c -> {
            lock(c,tenant,agent);
            String fingerprint=EventIdentity.sha256(List.of(agent,n));
            Operation prior=operation(c,tenant,"rollback",key);
            if(prior!=null) {
                require(prior.fingerprint().equals(fingerprint),"IDEMPOTENCY_CONFLICT");
                RollbackResult saved=codec.read(prior.result(),RollbackResult.class);
                return new Rollback(saved.digest(),Optional.ofNullable(saved.restoredSnapshot()));
            }
            Version target=version(c,tenant,agent,n);
            require(target!=null,"VERSION_NOT_FOUND");
            require(target.channel()==Channel.RELEASED,"VERSION_NOT_ACTIVE");
            Optional<Version> restored=Optional.empty();
            if(target.rollbackRef()!=null) {
                String expected="agentstore://"+tenant+"/"+agent+"/";
                require(target.rollbackRef().startsWith(expected),"INVALID_ROLLBACK_REF");
                long previousNumber=Long.parseLong(target.rollbackRef().substring(expected.length()));
                Version previous=version(c,tenant,agent,previousNumber);
                require(previous!=null && previous.channel()==Channel.VERIFIED,"ROLLBACK_TARGET_NOT_VERIFIED");
                Version active=previous.withChannel(Channel.RELEASED);
                updateVersion(c,active);
                transition(c,tenant,agent,active.version(),Channel.VERIFIED,Channel.RELEASED,
                    key,active.evidence().evaluationRunId(),Set.of());
                restored=Optional.of(active);
            }
            updateVersion(c,target.withChannel(Channel.ROLLED_BACK));
            transition(c,tenant,agent,n,Channel.RELEASED,Channel.ROLLED_BACK,
                key,target.evidence().evaluationRunId(),Set.of());
            recordOperation(c,tenant,"rollback",key,fingerprint,
                new RollbackResult(target.specDigest(),restored.orElse(null)));
            return new Rollback(target.specDigest(),restored);
        });
    }
    @Override public Optional<Version> active(String tenant,String agent) {
        return tx.transaction(c -> active(c,tenant,agent));
    }
    @Override public List<Version> versions(String tenant,String agent) {
        return tx.transaction(c -> versions(c,tenant,agent));
    }
    @Override public List<Transition> history(String tenant,String agent) {
        return tx.transaction(c -> {
            List<Transition> transitions=new ArrayList<>();
            try(PreparedStatement st=c.prepareStatement(
                "SELECT payload FROM cp_agent_transition WHERE tenant_id=? AND agent_id=? ORDER BY sequence_id")) {
                bind(st,tenant,agent);
                try(ResultSet rs=st.executeQuery()) {
                    while(rs.next()) transitions.add(codec.read(rs.getString(1),Transition.class));
                }
            }
            return List.copyOf(transitions);
        });
    }
}
