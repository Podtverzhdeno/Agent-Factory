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
                // Never send historical work after a transition or terminal decision.
                if (action.delivered || action.attempts>=5 ||
                    !Objects.equals(w.pendingOperationId,action.operationId) ||
                    !matchesPhase(w.state,action.type)) continue;
                // The call is outside the DB transaction. Replay requires an idempotent receiver.
                try {
                    Protocol.CommandReceipt receipt = deliver(w,action);
                    if (!receipt.accepted() || !Objects.equals(receipt.operationId(),action.operationId))
                        throw new Protocol.RemoteCommandFailure("REMOTE_RECEIPT_MISMATCH",false);
                    boolean acknowledged = ledger.transact(w.tenantId,w.workflowId,active -> {
                        if (!stillPending(active,action)) return false;
                        active.actions.stream().filter(a->a.operationId.equals(action.operationId))
                            .forEach(a->{ a.delivered=true; a.lastError=null; });
                        return true;
                    });
                    if (acknowledged) {
                        delivered.incrementAndGet();
                        ControlPlaneTelemetry.outbox(ControlPlaneTelemetry.Outcome.ACKNOWLEDGED,
                            w,action,action.attempts,null);
                    } else {
                        ControlPlaneTelemetry.outbox(ControlPlaneTelemetry.Outcome.SUPERSEDED,
                            w,action,action.attempts,null);
                    }
                } catch (RuntimeException exception) {
                    // Keep exception messages and bearer-token-bearing stack traces out of logs.
                    boolean permanent = exception instanceof Protocol.RemoteCommandFailure remote &&
                        !remote.retryable();
                    String safeCode = exception instanceof Protocol.RemoteCommandFailure remote
                        ? remote.getMessage() : "REMOTE_DISPATCH_EXCEPTION";
                    DispatchOutcome result=ledger.transact(w.tenantId,w.workflowId,active -> {
                        // A late failure must not poison a new/terminal workflow.
                        if (!stillPending(active,action))
                            return new DispatchOutcome(ControlPlaneTelemetry.Outcome.SUPERSEDED,
                                action.attempts,null);
                        int attempts=action.attempts;
                        for (Workflow.Action pending : active.actions) {
                            if (!pending.operationId.equals(action.operationId)) continue;
                            pending.attempts=permanent ? 5 : pending.attempts+1;
                            attempts=pending.attempts;
                            pending.lastError=exception.getClass().getSimpleName();
                            if (pending.attempts>=5) {
                                active.state=Workflow.State.BLOCKED;
                                active.errorCode=permanent ? safeCode : "OUTBOX_DELIVERY_EXHAUSTED";
                                active.requiredAction=permanent
                                    ? "resolve remote authorization or contract rejection"
                                    : "reconcile external operation before retry";
                                active.pendingOperationId=null;
                            }
                        }
                        return new DispatchOutcome(attempts>=5
                            ? ControlPlaneTelemetry.Outcome.BLOCKED
                            : ControlPlaneTelemetry.Outcome.RETRY_SCHEDULED,
                            attempts,attempts>=5 ? active.errorCode : safeCode);
                    });
                    ControlPlaneTelemetry.outbox(result.outcome(),w,action,
                        result.attempts(),result.errorCode());
                }
            }
        }
        return delivered.get();
    }
    private record DispatchOutcome(ControlPlaneTelemetry.Outcome outcome, int attempts, String errorCode) { }

    private static boolean stillPending(Workflow active, Workflow.Action sent) {
        return Objects.equals(active.pendingOperationId,sent.operationId) &&
            matchesPhase(active.state,sent.type) && active.actions.stream().anyMatch(a ->
                a.operationId.equals(sent.operationId) && !a.delivered && a.attempts < 5);
    }
    private static boolean matchesPhase(Workflow.State state, Workflow.ActionType type) {
        return switch (type) {
            case BUILD -> state==Workflow.State.BUILDING;
            case EVALUATE -> state==Workflow.State.TESTING || state==Workflow.State.RE_TESTING;
            case OPTIMIZE -> state==Workflow.State.OPTIMIZING;
            case SOUP -> state==Workflow.State.TRAINING;
        };
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
