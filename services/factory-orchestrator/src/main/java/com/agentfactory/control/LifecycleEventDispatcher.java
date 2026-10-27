package com.agentfactory.control;

/**
 * Outbox relay for workflow state notifications. It does not initiate builds.
 * The consumer must deduplicate stable eventIds: publish + acknowledgment is
 * at-least-once, never an exactly-once guarantee for business effects.
 */
public final class LifecycleEventDispatcher {
    private final Ports.WorkflowLedger ledger;
    private final Ports.OutboxPublisher publisher;
    public LifecycleEventDispatcher(Ports.WorkflowLedger ledger, Ports.OutboxPublisher publisher) {
        this.ledger = java.util.Objects.requireNonNull(ledger);
        this.publisher = java.util.Objects.requireNonNull(publisher);
    }
    public int publishPending() {
        int count=0;
        for (Ports.Key key : ledger.withUndeliveredEvents()) {
            Workflow snapshot=ledger.get(key.tenantId(), key.workflowId());
            for (long seq=snapshot.publishedAuditCount; seq<snapshot.audit.size(); seq++) {
                Workflow.Audit audit=snapshot.audit.get(Math.toIntExact(seq));
                LifecycleEvent event=new LifecycleEvent("0.1",
                    "cp:"+snapshot.tenantId.length()+":"+snapshot.tenantId+":"+
                    snapshot.workflowId.length()+":"+snapshot.workflowId+":lifecycle:"+(seq+1),
                    audit.occurredAt(),snapshot.tenantId,snapshot.workflowId,
                    audit.correlationId(),audit.from(),audit.to(),audit.reason(),seq+1);
                try {
                    publisher.publish(event);
                } catch (RuntimeException failure) {
                    // Event contents and publisher exception details are never logged.
                    ControlPlaneTelemetry.lifecycle(
                        ControlPlaneTelemetry.NotificationOutcome.PUBLISH_FAILED,event);
                    throw failure;
                }
                final long expected=seq;
                boolean acknowledged=ledger.transact(snapshot.tenantId,snapshot.workflowId,w -> {
                    if (w.publishedAuditCount!=expected) return false;
                    w.publishedAuditCount++;
                    return true;
                });
                ControlPlaneTelemetry.lifecycle(acknowledged
                    ? ControlPlaneTelemetry.NotificationOutcome.PUBLISHED
                    : ControlPlaneTelemetry.NotificationOutcome.SUPERSEDED,event);
                count++;
            }
        }
        return count;
    }
}
