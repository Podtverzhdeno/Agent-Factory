package com.agentfactory.control;

import com.agentfactory.store.AgentStore;
import com.agentfactory.store.InMemoryAgentStore;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import static com.agentfactory.control.Protocol.*;

/** Dependency-free executable component tests for offline CI and review. */
public final class ControlPlaneComponentTests {
    static final String TENANT="tenant-a", WF="workflow-01", SNAP="snap-001";
    static final String DATASET="artifact://eval/dataset-v1", POLICY="artifact://policy/acceptance-v1";
    static String hash(char c) { return "sha256:"+String.valueOf(c).repeat(64); }
    static final String SPEC1=hash('a'), SPEC2=hash('b'), MODEL=hash('c'), TOOL=hash('d');
    static final Instant NOW=Instant.parse("2026-10-27T10:00:00Z");
    static Principal actor(String tenant, String... scopes) {
        return new Principal("test-principal",tenant,Set.of(scopes));
    }
    static final Principal COMMAND=actor(TENANT,"factory:start","factory:read","factory:release","factory:rollback","factory:training");
    static final Principal EVENTS=actor(TENANT,"factory:events");
    static final AtomicInteger run=new AtomicInteger();
    static void test(String name,Runnable action) {
        try { action.run(); System.out.println("PASS "+name);run.incrementAndGet(); }
        catch(Throwable ex) { System.out.println("FAIL "+name+" "+ex); throw ex; }
    }
    static void check(boolean pass) { if(!pass) throw new AssertionError("assertion failed"); }
    static void error(String code,Runnable action) {
        try { action.run();throw new AssertionError("expected "+code); }
        catch(IllegalStateException ex) { check(ex.getMessage().contains(code)); }
    }
    static final class Fixture {
        final InMemoryWorkflowLedger ledger=new InMemoryWorkflowLedger();
        final InMemoryAgentStore store=new InMemoryAgentStore();
        final AtomicInteger builds=new AtomicInteger(), evals=new AtomicInteger(), opts=new AtomicInteger(), soups=new AtomicInteger();
        final Set<String> approvals=new HashSet<>();
        boolean auto;
        boolean failOnce;
        boolean invalidEvidence;
        final ControlPlane cp=new ControlPlane(ledger,(tenant,snap) ->
            new Snapshot(tenant,snap,"READY",hash('e'),POLICY,DATASET,"owner","r1"),
            (p,tenant,scope) -> { if(p==null || !tenant.equals(p.tenantId()) || !p.scopes().contains(scope))
                throw new IllegalStateException("UNAUTHORIZED_TENANT_OR_SCOPE"); },
            (t,w,purpose)-> approvals.contains(purpose), view->auto, ()->NOW,store,
            (tenant,run,digest,evidence)-> {
                if(invalidEvidence) throw new IllegalStateException("NOT_ATTESTED");
            });
        final OutboxDispatcher dispatcher=new OutboxDispatcher(ledger,
            command -> { builds.incrementAndGet(); if(failOnce) throw new IllegalStateException("down");
                return new CommandReceipt(command.operationId(),true); },
            command -> { evals.incrementAndGet();return new CommandReceipt(command.operationId(),true); },
            command -> { opts.incrementAndGet();return new CommandReceipt(command.operationId(),true); },
            command -> { soups.incrementAndGet();return new CommandReceipt(command.operationId(),true); });
        Start request(String id) {
            return new Start(TENANT,id,SNAP,"idem:"+id,new Limits(2,new BigDecimal("5.00"),NOW.plusSeconds(3600)),"correlation:"+id);
        }
        Workflow.View start() { return cp.start(COMMAND,request(WF)); }
        Workflow.View get() { return cp.get(COMMAND,TENANT,WF); }
        Header header(String event) {
            return new Header("0.1",event,TENANT,WF,get().pendingOperationId(),"correlation:"+WF,NOW);
        }
        void build() {
            dispatcher.dispatchPending();
            cp.onBuild(EVENTS,new BuildFinished(header("build-complete"),true,"agent-01",
                "artifact://agents/a1",SPEC1,Map.of("catalog.lookup",TOOL),MODEL,
                "artifact://a2a/card-v1",null,false));
        }
        AgentStore.Evidence evidence(boolean passed,boolean veto,boolean holdout,AgentStore.Risk risk, String digest) {
            return new AgentStore.Evidence("evaluation-1",digest,DATASET,SPEC1,"artifact://metrics/1",
                "artifact://traces/1",holdout?"artifact://holdout/1":null,true,passed,veto,true,true,risk,Set.of());
        }
        Workflow.View eval(boolean passed,boolean veto,boolean holdout,AgentStore.Risk risk, String digest, String cost) {
            dispatcher.dispatchPending();
            return cp.onEvaluation(EVENTS,new EvaluationFinished(header("eval-"+UUID.randomUUID()),
                "evaluation-1",digest,evidence(passed,veto,holdout,risk,digest),
                new BigDecimal(cost),null,false));
        }
        Workflow.View optimize(String cost) {
            dispatcher.dispatchPending();
            return cp.onOptimization(EVENTS,new OptimizationFinished(header("optimization-complete"),
                true,SPEC1,"artifact://agents/a2",SPEC2,new BigDecimal(cost),null,false));
        }
    }
    public static void main(String[] ignored) {
        test("AF-REQ-001 explicit authorized builder start",()->{
            Fixture f=new Fixture();check(f.start().state()==Workflow.State.BUILDING);
            check(f.builds.get()==0);check(f.dispatcher.dispatchPending()==1);check(f.builds.get()==1);
            check(f.dispatcher.dispatchPending()==0);
        });
        test("AF-REQ-010/011 repair then independent re-evaluation and gated release",()->{
            Fixture f=new Fixture();f.start();f.dispatcher.dispatchPending();f.build();
            check(f.get().state()==Workflow.State.TESTING);f.dispatcher.dispatchPending();check(f.evals.get()==1);
            check(f.eval(false,false,true,AgentStore.Risk.LOW,SPEC1,"0.30").state()==Workflow.State.OPTIMIZING);
            f.dispatcher.dispatchPending();check(f.opts.get()==1);
            check(f.optimize("0.20").state()==Workflow.State.RE_TESTING);
            f.dispatcher.dispatchPending();check(f.evals.get()==2);
            check(f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC2,"0.50").state()==Workflow.State.VERIFIED);
            check(f.store.active(TENANT,"agent-01").isEmpty());
            error("HUMAN_APPROVAL_REQUIRED",()->f.cp.release(COMMAND,TENANT,WF,"release1"));
            f.approvals.add("release:approve");
            check(f.cp.release(COMMAND,TENANT,WF,"release1").state()==Workflow.State.RELEASED);
            check(f.store.active(TENANT,"agent-01").orElseThrow().specDigest().equals(SPEC2));
            check(f.cp.release(COMMAND,TENANT,WF,"release1").releasedVersion()==1);
        });
        test("AF-REQ-014 auto promote only complete low risk evidence",()->{
            Fixture f=new Fixture();f.auto=true;f.start();f.build();
            check(f.eval(true,false,true,AgentStore.Risk.LOW,SPEC1,"0.1").state()==Workflow.State.RELEASED);
            check(f.store.active(TENANT,"agent-01").isPresent());
        });
        test("AF-REQ-009 critical safety veto blocks permanently",()->{
            Fixture f=new Fixture();f.auto=true;f.start();f.build();
            check(f.eval(false,true,true,AgentStore.Risk.LOW,SPEC1,"0.1").state()==Workflow.State.BLOCKED);
            check(f.opts.get()==0);check(f.store.active(TENANT,"agent-01").isEmpty());
        });
        test("AF-REQ-014 absent gold/holdout blocks",()->{
            Fixture f=new Fixture();f.start();f.build();
            check(f.eval(true,false,false,AgentStore.Risk.LOW,SPEC1,"0.1").errorCode().equals("INDEPENDENT_HOLDOUT_MISSING"));
        });
        test("AF-REQ-011 mismatched candidate digest rejected",()->{
            Fixture f=new Fixture();f.start();f.build();
            check(f.eval(true,false,true,AgentStore.Risk.LOW,SPEC2,"0.1").errorCode().equals("SPEC_VERSION_MISMATCH"));
        });
        test("AF-REQ-010 budget exhaustion stops repair",()->{
            Fixture f=new Fixture();f.start();f.build();
            check(f.eval(false,false,true,AgentStore.Risk.LOW,SPEC1,"6").errorCode().equals("SPEND_BUDGET_EXHAUSTED"));
        });
        test("AF-REQ-010 max repair attempts terminate",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(false,false,true,AgentStore.Risk.LOW,SPEC1,"0.1");f.optimize("0.1");
            f.eval(false,false,true,AgentStore.Risk.LOW,SPEC2,"0.1");
            check(f.get().repairs()==2);
            f.dispatcher.dispatchPending();
            f.cp.onOptimization(EVENTS,new OptimizationFinished(f.header("opt-2"),true,SPEC2,
                "artifact://agents/a3",hash('f'),new BigDecimal("0.1"),null,false));
            check(f.get().state()==Workflow.State.RE_TESTING);
            check(f.eval(false,false,true,AgentStore.Risk.LOW,hash('f'),"0.1").errorCode().equals("MAX_REPAIR_ATTEMPTS"));
        });
        test("AF-REQ-015 duplicate start returns same build and same version",()->{
            Fixture f=new Fixture();Workflow.View first=f.start();Workflow.View second=f.start();
            check(first.workflowId().equals(second.workflowId()));check(f.ledger.get(TENANT,WF).actions.size()==1);
            error("IDEMPOTENCY_CONFLICT",()->f.cp.start(COMMAND,new Start(TENANT,"different",SNAP,
                "idem:"+WF,new Limits(2,new BigDecimal("5.00"),NOW.plusSeconds(3600)),"correlation:"+WF)));
        });
        test("AF-REQ-020 deny cross-tenant read and event injection",()->{
            Fixture f=new Fixture();f.start();
            error("UNAUTHORIZED_TENANT_OR_SCOPE",()->f.cp.get(actor("tenant-b","factory:read"),TENANT,WF));
            error("UNAUTHORIZED_TENANT_OR_SCOPE",()->f.cp.onBuild(actor("tenant-b","factory:events"),
                new BuildFinished(f.header("malicious"),true,"agent-01","artifact://spec",SPEC1,
                    Map.of("tool",TOOL),MODEL,null,null,false)));
            check(f.get().state()==Workflow.State.BUILDING);
        });
        test("AF-REQ-015 duplicate completed event idempotent",()->{
            Fixture f=new Fixture();f.start();f.dispatcher.dispatchPending();
            BuildFinished event=new BuildFinished(f.header("b1"),true,
                "agent-01","artifact://agents/a1",SPEC1,Map.of("t",TOOL),MODEL,null,null,false);
            f.cp.onBuild(EVENTS,event);f.cp.onBuild(EVENTS,event);
            check(f.ledger.get(TENANT,WF).actions.size()==2);
            error("EVENT_ID_COLLISION",()->f.cp.onBuild(EVENTS,new BuildFinished(event.header(),false,
                null,null,null,null,null,null,"FAIL",false)));
        });
        test("AF-REQ-015 stale/out-of-order event ignored",()->{
            Fixture f=new Fixture();f.start();BuildFinished stale=new BuildFinished(new Header("0.1", "stale",
                TENANT,WF,"wrong-op","correlation:"+WF,NOW),true,"agent", "artifact://agents/a",SPEC1,
                Map.of("t",TOOL),MODEL,null,null,false);
            check(f.cp.onBuild(EVENTS,stale).state()==Workflow.State.BUILDING);
            check(f.ledger.get(TENANT,WF).actions.size()==1);
        });
        test("AF-REQ-015 outbox at-least-once retries, stops after bounded attempts",()->{
            Fixture f=new Fixture();f.failOnce=true;f.start();
            for(int i=0;i<5;i++) check(f.dispatcher.dispatchPending()==0);
            check(f.get().errorCode().equals("OUTBOX_DELIVERY_EXHAUSTED"));
            check(f.dispatcher.dispatchPending()==0);
        });
        test("AF-REQ-014 no version on unpinned build artifact",()->{
            Fixture f=new Fixture();f.start();f.dispatcher.dispatchPending();
            Workflow.View result=f.cp.onBuild(EVENTS,
                new BuildFinished(f.header("build-invalid"),true,"agent-01","artifact://bad", "not-a-digest",
                Map.of("t",TOOL),MODEL,null,null,false));
            check(result.errorCode().equals("INVALID_AGENT_SPEC"));check(f.store.versions(TENANT,"agent-01").isEmpty());
        });
        test("AF-REQ-015 rollback removes active release",()->{
            Fixture f=new Fixture();f.auto=true;f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.LOW,SPEC1,"0.1");
            error("ROLLBACK_APPROVAL_REQUIRED",()->f.cp.rollback(COMMAND,TENANT,WF,"rb-1"));
            f.approvals.add("rollback:approve");
            check(f.cp.rollback(COMMAND,TENANT,WF,"rb-1").state()==Workflow.State.ROLLED_BACK);
            check(f.store.active(TENANT,"agent-01").isEmpty());
            check(f.store.versions(TENANT,"agent-01").get(0).channel()==AgentStore.Channel.ROLLED_BACK);
        });
        test("AF-REQ-017 Soup requires independent rights and command",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1");
            error("TRAINING_RIGHTS_OR_APPROVAL_MISSING",()->f.cp.requestSoup(COMMAND,TENANT,WF,"artifact://rights/valid"));
            f.approvals.add("training:approve");
            check(f.cp.requestSoup(COMMAND,TENANT,WF,"artifact://rights/valid").state()==Workflow.State.TRAINING);
            f.dispatcher.dispatchPending();check(f.soups.get()==1);
            check(f.opts.get()==0);
        });
        test("AF-REQ-015 stale event cannot acknowledge future outbox",()->{
            Fixture f=new Fixture();f.start();
            f.cp.onBuild(EVENTS,new BuildFinished(new Header("0.1","stale-1",TENANT,WF,
                "incorrect-op","correlation:"+WF,NOW),false,null,null,null,null,null,null,"bad",false));
            check(f.dispatcher.dispatchPending()==1);
            check(f.builds.get()==1);
        });
        test("AF-REQ-017 Soup result cannot impersonate GEPARD",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1");
            f.approvals.add("training:approve");
            f.cp.requestSoup(COMMAND,TENANT,WF,"artifact://rights/valid");
            f.dispatcher.dispatchPending();
            check(f.cp.onOptimization(EVENTS,
                new OptimizationFinished(f.header("forged-gepard"),true,SPEC1,
                    "artifact://agents/poison",SPEC2,new BigDecimal("0"),null,false))
                .state()==Workflow.State.TRAINING);
            check(f.get().state()==Workflow.State.TRAINING);
        });
        test("AF-REQ-014 high risk never auto promotes",()->{
            Fixture f=new Fixture();f.auto=true;f.start();f.build();
            check(f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1").state()==Workflow.State.VERIFIED);
            check(f.store.active(TENANT,"agent-01").isEmpty());
        });
        test("AF-REQ-020 authorization precedes idempotency lookup",()->{
            Fixture f=new Fixture();f.start();
            error("UNAUTHORIZED_TENANT_OR_SCOPE",()->f.cp.start(actor("tenant-b","factory:start"), f.request(WF)));
        });
        test("AF-REQ-014 mismatched evidence run id rejected",()->{
            Fixture f=new Fixture();f.start();f.build();
            AgentStore.Evidence e=f.evidence(true,false,true,AgentStore.Risk.LOW,SPEC1);
            f.dispatcher.dispatchPending();
            Workflow.View out=f.cp.onEvaluation(EVENTS,new EvaluationFinished(f.header("bad-run-id"),
                "different-evaluation-run",SPEC1,e,new BigDecimal("0.1"),null,false));
            check(out.errorCode().equals("SPEC_VERSION_MISMATCH"));
            check(f.store.active(TENANT,"agent-01").isEmpty());
        });
        test("AF-REQ-001 early completion cannot bypass direct Builder receipt",()->{
            Fixture f=new Fixture();f.start();
            BuildFinished early=new BuildFinished(f.header("early"),true,"agent-01",
                "artifact://agents/a1",SPEC1,Map.of("t",TOOL),MODEL,null,null,false);
            check(f.cp.onBuild(EVENTS,early).state()==Workflow.State.BUILDING);
            check(f.dispatcher.dispatchPending()==1);
            check(f.cp.onBuild(EVENTS,early).state()==Workflow.State.TESTING);
        });
        test("AF-REQ-014 forged evaluator attestation is BLOCKED",()->{
            Fixture f=new Fixture();f.invalidEvidence=true;f.start();f.build();
            check(f.eval(true,false,true,AgentStore.Risk.LOW,SPEC1,"0.1")
                .errorCode().equals("UNTRUSTED_EVALUATION_EVIDENCE"));
            check(f.store.active(TENANT,"agent-01").isEmpty());
        });
        test("AF-REQ-010 non-repairable connector absence prevents GEPARD",()->{
            Fixture f=new Fixture();f.start();f.build();f.dispatcher.dispatchPending();
            AgentStore.Evidence e=f.evidence(false,false,true,AgentStore.Risk.LOW,SPEC1);
            Workflow.View v=f.cp.onEvaluation(EVENTS,new EvaluationFinished(f.header("missing-tool"),
                "evaluation-1",SPEC1,e,new BigDecimal("0.1"),"MISSING_CAPABILITY",false));
            check(v.state()==Workflow.State.BLOCKED);
            check(v.errorCode().equals("MISSING_CAPABILITY"));
            check(f.opts.get()==0);
        });
        test("AF-REQ-017 Soup result creates immutable new candidate and re-evaluation",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1");
            f.approvals.add("training:approve");
            f.cp.requestSoup(COMMAND,TENANT,WF,"artifact://rights/valid");
            check(f.dispatcher.dispatchPending()==1);
            check(f.cp.onSoup(EVENTS,new SoupFinished(f.header("soup-done"),true,SPEC1,
                "artifact://agents/trained",SPEC2,hash('f'),new BigDecimal("0.4"),null,false))
                .state()==Workflow.State.RE_TESTING);
            check(f.dispatcher.dispatchPending()==1);
            check(f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC2,"0.2").state()==Workflow.State.VERIFIED);
            check(f.store.active(TENANT,"agent-01").isEmpty());
            check(f.store.versions(TENANT,"agent-01").size()==2);
        });
        test("AF-REQ-015 obsolete undelivered outbox cannot dispatch",()->{
            Fixture f=new Fixture();f.start();
            f.ledger.transact(TENANT,WF,w->{w.state=Workflow.State.BLOCKED;
                w.errorCode="MANUAL_CANCEL";w.pendingOperationId=null;return null;});
            check(f.dispatcher.dispatchPending()==0);
            check(f.builds.get()==0);
        });
        System.out.println("COMPONENT TESTS PASSED: "+run.get());
    }
}
