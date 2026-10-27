package com.agentfactory.control;

import java.util.Objects;
import java.util.concurrent.atomic.AtomicInteger;

/** Direct REST client port dispatcher. At-least-once delivery with deterministic idempotency keys. */
public final class OutboxDispatcher {
    private final Ports.WorkflowLedger ledger;
    private final Ports.BuildClient builder;
    private final Ports.EvaluationClient evaluator;
    private final Ports.OptimizationClient optimizer;
    private final Ports.SoupClient soup;
    public OutboxDispatcher(Ports.WorkflowLedger ledger, Ports.BuildClient builder,
                            Ports.EvaluationClient evaluator, Ports.OptimizationClient optimizer,
                            Ports.SoupClient soup) {
        this.ledger=ledger; this.builder=builder; this.evaluator=evaluator;
        this.optimizer=optimizer; this.soup=soup;
    }
    public int dispatchPending() {
        AtomicInteger delivered = new AtomicInteger();
        for (Ports.Key key : ledger.withUndeliveredActions()) {
            Workflow w = ledger.get(key.tenantId(),key.workflowId());
            for (Workflow.Action action : w.actions) {
                if (action.delivered || action.attempts>=5) continue;
                // The call is outside the DB transaction. Replay requires an idempotent receiver.
                try {
                    Protocol.CommandReceipt receipt = deliver(w,action);
                    if (!receipt.accepted() || !Objects.equals(receipt.operationId(),action.operationId))
                        throw new IllegalStateException("REMOTE_RECEIPT_MISMATCH");
                    ledger.transact(w.tenantId,w.workflowId,active -> {
                        active.actions.stream().filter(a->a.operationId.equals(action.operationId))
                            .forEach(a->{ a.delivered=true; a.lastError=null; });
                        return null;
                    });
                    delivered.incrementAndGet();
                } catch (RuntimeException exception) {
                    ledger.transact(w.tenantId,w.workflowId,active -> {
                        active.actions.stream().filter(a->a.operationId.equals(action.operationId))
                            .forEach(a->{ a.attempts++; a.lastError=exception.getClass().getSimpleName();
                                if(a.attempts>=5 && active.state!=Workflow.State.RELEASED &&
                                    active.state!=Workflow.State.ROLLED_BACK) {
                                    active.state=Workflow.State.BLOCKED;
                                    active.errorCode="OUTBOX_DELIVERY_EXHAUSTED";
                                    active.requiredAction="reconcile external operation before retry";
                                    active.pendingOperationId=null;
                                }
                            });
                        return null;
                    });
                }
            }
        }
        return delivered.get();
    }
    private Protocol.CommandReceipt deliver(Workflow w, Workflow.Action a) {
        return switch (a.type) {
            case BUILD -> builder.submit(new Protocol.BuildCommand(w.tenantId,w.workflowId,
                w.taskSnapshotId,w.snapshotDigest,a.operationId,a.idempotencyKey,w.correlationId,w.policyRef));
            case EVALUATE -> evaluator.submit(new Protocol.EvaluationCommand(w.tenantId,w.workflowId,
                a.operationId,a.specRef,a.specDigest,w.baselineDigest,w.datasetRef,w.policyRef,
                a.idempotencyKey,w.correlationId));
            case OPTIMIZE -> optimizer.submit(new Protocol.OptimizationCommand(w.tenantId,w.workflowId,
                a.operationId,a.specRef,a.specDigest,w.baselineRef,w.baselineDigest,w.datasetRef,
                "system_prompt,harness_graph",a.idempotencyKey,w.correlationId));
            case SOUP -> soup.submit(new Protocol.SoupCommand(w.tenantId,w.workflowId,a.operationId,
                w.specRef,w.baselineDigest,a.specRef,a.idempotencyKey,w.correlationId));
        };
    }
}
