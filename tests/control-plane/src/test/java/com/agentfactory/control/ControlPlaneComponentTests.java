package com.agentfactory.control;

import com.agentfactory.store.AgentStore;
import com.agentfactory.store.InMemoryAgentStore;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
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
    static final Principal EVENTS=actor(TENANT,"factory:events:build","factory:events:evaluation",
        "factory:events:optimization","factory:events:soup");
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
        final AtomicReference<Instant> now=new AtomicReference<>(NOW);
        final ControlPlane cp=new ControlPlane(ledger,(tenant,snap) ->
            new Snapshot(tenant,snap,"READY",hash('e'),POLICY,DATASET,"owner","r1"),
            (p,tenant,scope) -> { if(p==null || !tenant.equals(p.tenantId()) || !p.scopes().contains(scope))
                throw new IllegalStateException("UNAUTHORIZED_TENANT_OR_SCOPE"); },
            (t,w,purpose)-> approvals.contains(purpose), view->auto, now::get,store,
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
        test("AF-REQ-015 replay remains stable past expiry and correlation mismatch conflicts",()->{
            Fixture f=new Fixture();
            Workflow.View accepted=f.start();
            f.now.set(NOW.plusSeconds(3601));
            Workflow.View replay=f.cp.start(COMMAND,f.request(WF));
            check(replay.workflowId().equals(accepted.workflowId()));
            check(replay.revision()==accepted.revision());
            check(f.ledger.get(TENANT,WF).actions.size()==1);
            error("IDEMPOTENCY_CONFLICT",()->f.cp.start(COMMAND,
                new Start(TENANT,WF,SNAP,"idem:"+WF,
                    new Limits(2,new BigDecimal("5.00"),NOW.plusSeconds(3600)),
                    "different-correlation")));
            error("UNAUTHORIZED_TENANT_OR_SCOPE",()->f.cp.start(
                actor("tenant-b","factory:start"),f.request(WF)));
            error("TIME_BUDGET_EXHAUSTED",()->f.cp.start(COMMAND,
                new Start(TENANT,"expired-new",SNAP,"idem:expired-new",
                    new Limits(2,new BigDecimal("5.00"),NOW.plusSeconds(3600)),
                    "expired-correlation")));
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
        test("AF-REQ-015 release and rollback replay survive approval revocation",()->{
            Fixture f=new Fixture();f.start();f.build();
            check(f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1")
                .state()==Workflow.State.VERIFIED);
            f.approvals.add("release:approve");
            Workflow.View released=f.cp.release(COMMAND,TENANT,WF,"release-1");
            check(released.state()==Workflow.State.RELEASED);
            f.approvals.remove("release:approve");
            check(f.cp.release(COMMAND,TENANT,WF,"release-1").state()==Workflow.State.RELEASED);
            check(f.store.history(TENANT,"agent-01").stream()
                .filter(t->t.to()==AgentStore.Channel.RELEASED).count()==1);
            f.approvals.add("rollback:approve");
            check(f.cp.rollback(COMMAND,TENANT,WF,"rollback-1")
                .state()==Workflow.State.ROLLED_BACK);
            f.approvals.remove("rollback:approve");
            check(f.cp.rollback(COMMAND,TENANT,WF,"rollback-1")
                .state()==Workflow.State.ROLLED_BACK);
            check(f.store.history(TENANT,"agent-01").stream()
                .filter(t->t.to()==AgentStore.Channel.ROLLED_BACK).count()==1);
        });
        test("AF-REQ-017 Soup replay survives approval revocation without new effects",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1");
            f.approvals.add("training:approve");
            Workflow.View original=f.cp.requestSoup(COMMAND,TENANT,WF,
                "artifact://rights/valid","train-replay-1");
            f.approvals.remove("training:approve");
            check(f.cp.requestSoup(COMMAND,TENANT,WF,
                "artifact://rights/valid","train-replay-1").state()==Workflow.State.TRAINING);
            check(f.get().trainingAttempts()==1);
            check(f.dispatcher.dispatchPending()==1);
            check(f.soups.get()==1);
            error("TRAINING_RIGHTS_OR_APPROVAL_MISSING",()->f.cp.requestSoup(
                COMMAND,TENANT,WF,"artifact://rights/valid","different-key"));
        });
        test("AF-REQ-015 inbox compares map payloads independent of order and mutation",()->{
            Fixture f=new Fixture();f.start();check(f.dispatcher.dispatchPending()==1);
            Header same=f.header("build-immutable-event");
            Map<String,String> original=new LinkedHashMap<>();
            original.put("b",TOOL);original.put("a",hash('f'));
            BuildFinished first=new BuildFinished(same,true,"agent-01",
                "artifact://agents/a1",SPEC1,original,MODEL,null,null,false);
            original.put("b",hash('e'));
            check(first.toolDigests().get("b").equals(TOOL));
            check(f.cp.onBuild(EVENTS,first).state()==Workflow.State.TESTING);
            Map<String,String> reordered=new LinkedHashMap<>();
            reordered.put("a",hash('f'));reordered.put("b",TOOL);
            BuildFinished replay=new BuildFinished(same,true,"agent-01",
                "artifact://agents/a1",SPEC1,reordered,MODEL,null,null,false);
            check(f.cp.onBuild(EVENTS,replay).state()==Workflow.State.TESTING);
            check(f.ledger.get(TENANT,WF).actions.size()==2);
            reordered.put("b",hash('e'));
            check(replay.toolDigests().get("b").equals(TOOL));
            error("EVENT_ID_COLLISION",()->f.cp.onBuild(EVENTS,
                new BuildFinished(same,true,"agent-01","artifact://agents/a1",
                    SPEC1,Map.of("a",hash('f'),"b",hash('e')),MODEL,null,null,false)));
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
            error("EVENT_AWAITING_COMMAND_RECEIPT",()->f.cp.onBuild(EVENTS,early));
            check(f.get().state()==Workflow.State.BUILDING);
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
        test("AF-REQ-015 append-only release transition history survives rollback",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1");
            f.approvals.add("release:approve");
            f.cp.release(COMMAND,TENANT,WF,"first");
            AgentStore.Evidence e=f.evidence(true,false,true,AgentStore.Risk.HIGH,SPEC2);
            AgentStore.Version second=f.store.registerCandidate(new AgentStore.Metadata(TENANT,
                "agent-01","artifact://agents/a2",SPEC2,Map.of("t",TOOL),MODEL,
                "artifact://a2a/card-v2",e),"candidate:second");
            check(second.version()==2);
            f.store.promote(TENANT,"agent-01",second.version(),"second-release",
                Set.of("release:approve"),false);
            check(f.store.active(TENANT,"agent-01").orElseThrow().version()==2);
            check(f.store.rollback(TENANT,"agent-01",2,"second-rollback").restored().orElseThrow().version()==1);
            check(f.store.active(TENANT,"agent-01").orElseThrow().version()==1);
            check(f.store.history(TENANT,"agent-01").size()==7);
            check(f.store.history(TENANT,"agent-01").stream().anyMatch(t ->
                t.to()==AgentStore.Channel.ROLLED_BACK && t.version()==2));
        });
        test("AF-REQ-020 AgentStore releases isolated per tenant",()->{
            Fixture f=new Fixture();f.auto=true;f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.LOW,SPEC1,"0.1");
            check(f.store.active("other-tenant","agent-01").isEmpty());
            check(f.store.history("other-tenant","agent-01").isEmpty());
            check(f.store.versions("other-tenant","agent-01").isEmpty());
        });
        test("AF-REQ-020 Builder publisher cannot forge an Evaluation event",()->{
            Fixture f=new Fixture();f.start();f.build();f.dispatcher.dispatchPending();
            error("UNAUTHORIZED_TENANT_OR_SCOPE",()->f.cp.onEvaluation(
                actor(TENANT,"factory:events:build"),
                new EvaluationFinished(f.header("forged-evaluation"),"evaluation-1",SPEC1,
                    f.evidence(true,false,true,AgentStore.Risk.LOW,SPEC1),
                    new BigDecimal("0.1"),null,false)));
            check(f.get().state()==Workflow.State.TESTING);
        });
        test("AF-REQ-015 AgentStore replay cannot change verified metadata",()->{
            Fixture f=new Fixture();
            AgentStore.Evidence e=f.evidence(true,false,true,AgentStore.Risk.HIGH,SPEC1);
            AgentStore.Metadata m=new AgentStore.Metadata(TENANT,"agent-01",
                "artifact://agents/a1",SPEC1,Map.of("catalog.lookup",TOOL),MODEL,null,e);
            check(f.store.registerCandidate(m,"key-1").version()==1);
            check(f.store.registerCandidate(m,"key-1").version()==1);
            error("IDEMPOTENCY_CONFLICT",()->f.store.registerCandidate(
                new AgentStore.Metadata(TENANT,"agent-01","artifact://agents/a1",SPEC1,
                    Map.of("catalog.lookup",hash('f')),MODEL,null,e),"key-1"));
            check(f.store.versions(TENANT,"agent-01").size()==1);
        });
        test("AF-REQ-017 Soup duplicate command queues one job",()->{
            Fixture f=new Fixture();f.start();f.build();
            f.eval(true,false,true,AgentStore.Risk.HIGH,SPEC1,"0.1");
            f.approvals.add("training:approve");
            check(f.cp.requestSoup(COMMAND,TENANT,WF,"artifact://rights/valid","train-1")
                .state()==Workflow.State.TRAINING);
            check(f.cp.requestSoup(COMMAND,TENANT,WF,"artifact://rights/valid","train-1")
                .trainingAttempts()==1);
            error("IDEMPOTENCY_CONFLICT",()->f.cp.requestSoup(COMMAND,TENANT,WF,
                "artifact://rights/changed","train-1"));
            check(f.dispatcher.dispatchPending()==1);
            check(f.soups.get()==1);
        });
        test("AF-REQ-010 no Builder completion after deadline",()->{
            Fixture f=new Fixture();f.start();check(f.dispatcher.dispatchPending()==1);
            f.now.set(NOW.plusSeconds(3601));
            check(f.cp.onBuild(EVENTS,new BuildFinished(f.header("late-build"),true,
                "agent-01","artifact://agents/a1",SPEC1,Map.of("catalog.lookup",TOOL),
                MODEL,null,null,false)).errorCode().equals("TIME_BUDGET_EXHAUSTED"));
            check(f.evals.get()==0);
            check(f.dispatcher.dispatchPending()==0);
        });
        test("AF-REQ-015 response revision and audit reason committed",()->{
            Fixture f=new Fixture();f.start();f.dispatcher.dispatchPending();
            Workflow.View out=f.cp.onBuild(EVENTS,new BuildFinished(f.header("invalid"),true,
                "agent-01","artifact://agents/bad","broken",Map.of("tool",TOOL),MODEL,
                null,null,false));
            check(out.revision()==f.get().revision());
            check(f.cp.audit(COMMAND,TENANT,WF).getLast().reason().equals("INVALID_AGENT_SPEC"));
        });
        test("AF-REQ-015 premature evaluation completion is retryable",()->{
            Fixture f=new Fixture();f.start();f.dispatcher.dispatchPending();f.build();
            AgentStore.Evidence e=f.evidence(true,false,true,AgentStore.Risk.HIGH,SPEC1);
            EvaluationFinished early=new EvaluationFinished(f.header("eval-early"),
                "evaluation-1",SPEC1,e,new BigDecimal("0.1"),null,false);
            error("EVENT_AWAITING_COMMAND_RECEIPT",()->f.cp.onEvaluation(EVENTS,early));
            check(f.get().state()==Workflow.State.TESTING);
            check(f.dispatcher.dispatchPending()==1);
            check(f.cp.onEvaluation(EVENTS,early).state()==Workflow.State.VERIFIED);
        });
        test("AF-REQ-010 deadline sweep stops orphan workflows and suppresses outbox",()->{
            Fixture f=new Fixture();f.start();
            f.now.set(NOW.plusSeconds(4000));
            check(f.cp.expireDueWorkflows()==1);
            check(f.cp.expireDueWorkflows()==0);
            check(f.get().errorCode().equals("TIME_BUDGET_EXHAUSTED"));
            check(f.dispatcher.dispatchPending()==0);
            check(f.builds.get()==0);
        });
        test("AF-REQ-020 incomplete event header rejected without NPE",()->{
            Fixture f=new Fixture();f.start();
            Header invalid=new Header("0.1","event-x",null,WF,"build-op","correlation:"+WF,NOW);
            error("INVALID_EVENT_HEADER",()->f.cp.onBuild(EVENTS,new BuildFinished(invalid,
                true,"agent-01","artifact://agents/a1",SPEC1,Map.of("t",TOOL),
                MODEL,null,null,false)));
            check(f.get().state()==Workflow.State.BUILDING);
        });
        test("AF-REQ-015 event collision uses structural equality, not toString",()->{
            Fixture f=new Fixture();f.start();f.dispatcher.dispatchPending();
            Map<String,String> crafted=new LinkedHashMap<>();
            crafted.put("a", "bad, b=other");
            Map<String,String> other=new LinkedHashMap<>();
            other.put("a", "bad");other.put("b", "other");
            check(crafted.toString().equals(other.toString()));
            Header h=f.header("same-event-id");
            BuildFinished one=new BuildFinished(h,true,"agent-01","artifact://agents/a1",
                SPEC1,crafted,MODEL,null,null,false);
            BuildFinished two=new BuildFinished(h,true,"agent-01","artifact://agents/a1",
                SPEC1,other,MODEL,null,null,false);
            check(one.toString().equals(two.toString()));
            check(f.cp.onBuild(EVENTS,one).state()==Workflow.State.BLOCKED);
            error("EVENT_ID_COLLISION",()->f.cp.onBuild(EVENTS,two));
        });
        test("AF-REQ-014 manual approval cannot bypass auto-promotion risk gate",()->{
            Fixture f=new Fixture();
            AgentStore.Evidence e=f.evidence(true,false,true,AgentStore.Risk.HIGH,SPEC1);
            AgentStore.Metadata m=new AgentStore.Metadata(TENANT,"agent-01",
                "artifact://agents/a1",SPEC1,Map.of("catalog.lookup",TOOL),MODEL,null,e);
            long v=f.store.registerCandidate(m,"candidate-high").version();
            error("HUMAN_APPROVAL_REQUIRED",()->f.store.promote(TENANT,"agent-01",v,
                "bad-auto",Set.of("release:approve"),true));
            check(f.store.active(TENANT,"agent-01").isEmpty());
            check(f.store.promote(TENANT,"agent-01",v,"approved-manual",
                Set.of("release:approve"),false).channel()==AgentStore.Channel.RELEASED);
        });
        test("AF-REQ-020 null event payloads return typed domain errors",()->{
            Fixture f=new Fixture();f.start();
            error("INVALID_EVENT",()->f.cp.onBuild(EVENTS,null));
            error("INVALID_EVENT",()->f.cp.onEvaluation(EVENTS,null));
            error("INVALID_EVENT",()->f.cp.onOptimization(EVENTS,null));
            error("INVALID_EVENT",()->f.cp.onSoup(EVENTS,null));
            check(f.get().state()==Workflow.State.BUILDING);
        });
        test("AF-REQ-015 lifecycle relay publishes stable events without starting work",()->{
            Fixture f=new Fixture();f.start();
            List<LifecycleEvent> received=new ArrayList<>();
            LifecycleEventDispatcher relay=new LifecycleEventDispatcher(f.ledger,received::add);
            check(relay.publishPending()==2);
            check(received.get(0).currentState()==Workflow.State.READY);
            check(received.get(1).currentState()==Workflow.State.BUILDING);
            check(received.stream().allMatch(e -> e.schemaVersion().equals("0.1") &&
                e.tenantId().equals(TENANT) && e.correlationId().equals("correlation:"+WF)));
            check(relay.publishPending()==0);
            check(f.builds.get()==0);
            f.build();
            check(relay.publishPending()==1);
            check(received.get(2).currentState()==Workflow.State.TESTING);
            check(relay.publishPending()==0);
        });
        test("AF-REQ-015 lifecycle relay retries after transient publisher failure",()->{
            Fixture f=new Fixture();f.start();
            AtomicInteger publishAttempts=new AtomicInteger();
            List<LifecycleEvent> observed=new ArrayList<>();
            LifecycleEventDispatcher relay=new LifecycleEventDispatcher(f.ledger,e -> {
                if (publishAttempts.getAndIncrement()==0) throw new IllegalStateException("broker_down");
                observed.add(e);
            });
            error("broker_down",relay::publishPending);
            check(relay.publishPending()==2);
            check(observed.size()==2);
            check(observed.get(0).eventId().endsWith(":lifecycle:1"));
            check(relay.publishPending()==0);
        });
        System.out.println("COMPONENT TESTS PASSED: "+run.get());
    }
}
