package com.agentfactory.api;

import com.agentfactory.control.*;
import com.agentfactory.store.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import java.time.Instant;

/**
 * Fail-closed development wiring. Replace each port explicitly after owner-ratified ADR,
 * persistence implementation, verified service endpoints and integration security review.
 * No implicit access to any MCP, secrets or customer tenants.
 */
@Configuration
public class SpringWiring {
    @Bean @ConditionalOnMissingBean(Ports.WorkflowLedger.class)
    Ports.WorkflowLedger workflowLedger() { return new InMemoryWorkflowLedger(); }

    @Bean @ConditionalOnMissingBean(AgentStore.class)
    AgentStore agentStore() { return new InMemoryAgentStore(); }

    @Bean @ConditionalOnMissingBean(Ports.TaskSnapshotReader.class)
    Ports.TaskSnapshotReader snapshotReader() {
        return (tenant, id) -> { throw new IllegalStateException("TASK_INTAKE_NOT_CONFIGURED"); };
    }

    @Bean @ConditionalOnMissingBean(Ports.TimeSource.class)
    Ports.TimeSource timeSource() { return Instant::now; }

    @Bean @ConditionalOnMissingBean(Ports.ApprovalReader.class)
    Ports.ApprovalReader approvalReader() { return (tenant, workflow, purpose) -> false; }

    @Bean @ConditionalOnMissingBean(Ports.ReleasePolicy.class)
    Ports.ReleasePolicy releasePolicy() { return view -> false; }

    @Bean @ConditionalOnMissingBean(Ports.TenantAuthz.class)
    Ports.TenantAuthz authorization() {
        return (actor, tenant, scope) -> {
            if (actor == null || !tenant.equals(actor.tenantId()) || !actor.scopes().contains(scope))
                throw new IllegalStateException("UNAUTHORIZED_TENANT_OR_SCOPE");
        };
    }

    @Bean @ConditionalOnMissingBean(ControlPlane.class)
    ControlPlane controlPlane(Ports.WorkflowLedger ledger, Ports.TaskSnapshotReader reader,
                              Ports.TenantAuthz authz, Ports.ApprovalReader approvals,
                              Ports.ReleasePolicy releasePolicy, Ports.TimeSource clock, AgentStore store) {
        return new ControlPlane(ledger, reader, authz, approvals, releasePolicy, clock, store);
    }
}
