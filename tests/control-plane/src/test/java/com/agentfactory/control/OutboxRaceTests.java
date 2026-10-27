package com.agentfactory.control;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicInteger;

/** Regression: an external callback can arrive after the workflow has been terminated. */
public final class OutboxRaceTests {
    private OutboxRaceTests() { }
    private static final String TENANT="tenant-a", WORKFLOW="wf-race";
    private static InMemoryWorkflowLedger pending() {
        var ledger=new InMemoryWorkflowLedger();
        var request=new Protocol.Start(TENANT,WORKFLOW,"snapshot","idempotency-01",
            new Protocol.Limits(1,new BigDecimal("1.0"),Instant.parse("2027-01-01T00:00:00Z")),"correlation-01");
        var snapshot=new Protocol.Snapshot(TENANT,"snapshot","READY","sha256:"+"a".repeat(64),
            "artifact://policies/v1","artifact://datasets/v1","tester","revision1");
        var workflow=new Workflow(request,snapshot);
        workflow.state=Workflow.State.BUILDING;
        workflow.enqueue(Workflow.ActionType.BUILD,null,null);
        ledger.open(workflow);
        return ledger;
    }
    private static OutboxDispatcher withBuilder(InMemoryWorkflowLedger ledger, Ports.BuildClient builder) {
        return new OutboxDispatcher(ledger,builder,
            x -> { throw new AssertionError("Unexpected Evaluation"); },
            x -> { throw new AssertionError("Unexpected optimization"); },
            x -> { throw new AssertionError("Unexpected Soup"); });
    }
    private static void check(boolean valid) {
        if(!valid) throw new AssertionError("Outbox late receipt broke workflow safety");
    }
    private static void block(InMemoryWorkflowLedger ledger) {
        ledger.transact(TENANT,WORKFLOW,w -> {
            w.state=Workflow.State.BLOCKED;
            w.errorCode="TIME_BUDGET_EXHAUSTED";
            w.pendingOperationId=null;
            return null;
        });
    }
    public static void main(String[] args) {
        var lateFailure=pending();
        lateFailure.transact(TENANT,WORKFLOW,w -> {w.actions.getFirst().attempts=4;return null;});
        check(withBuilder(lateFailure,command -> {
            block(lateFailure);
            throw new IllegalStateException("remote-failed-after-deadline");
        }).dispatchPending()==0);
        var failed=lateFailure.get(TENANT,WORKFLOW);
        check(failed.state==Workflow.State.BLOCKED);
        check("TIME_BUDGET_EXHAUSTED".equals(failed.errorCode));
        check(failed.actions.getFirst().attempts==4);

        var lateSuccess=pending();
        check(withBuilder(lateSuccess,command -> {
            block(lateSuccess);
            return new Protocol.CommandReceipt(command.operationId(),true);
        }).dispatchPending()==0);
        var succeeded=lateSuccess.get(TENANT,WORKFLOW);
        check(succeeded.state==Workflow.State.BLOCKED);
        check(!succeeded.actions.getFirst().delivered);
        check("TIME_BUDGET_EXHAUSTED".equals(succeeded.errorCode));

        var superseded=pending();
        superseded.transact(TENANT,WORKFLOW,w -> {w.actions.getFirst().attempts=4;return null;});
        check(withBuilder(superseded,command -> {
            superseded.transact(TENANT,WORKFLOW,w -> {
                w.state=Workflow.State.TESTING;
                w.enqueue(Workflow.ActionType.EVALUATE,"artifact://agents/candidate","sha256:"+"a".repeat(64));
                return null;
            });
            throw new IllegalStateException("old-builder-response");
        }).dispatchPending()==0);
        var afterTransition=superseded.get(TENANT,WORKFLOW);
        check(afterTransition.state==Workflow.State.TESTING);
        check(afterTransition.actions.getFirst().attempts==4);
        check(afterTransition.pendingOperationId.equals(afterTransition.actions.get(1).operationId));
        check(afterTransition.errorCode==null);

        var ordinary=pending();
        AtomicInteger calls=new AtomicInteger();
        var relay=withBuilder(ordinary,command -> {
            calls.incrementAndGet();
            return new Protocol.CommandReceipt(command.operationId(),true);
        });
        check(relay.dispatchPending()==1);
        check(relay.dispatchPending()==0);
        check(calls.get()==1 && ordinary.get(TENANT,WORKFLOW).actions.getFirst().delivered);
        System.out.println("OUTBOX RACE TESTS PASSED: 4");
    }
}
