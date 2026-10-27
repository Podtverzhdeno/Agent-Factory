package com.agentfactory.control;

import com.agentfactory.store.AgentStore;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import static com.agentfactory.control.Protocol.*;

/** Framework-independent control-plane; only explicit commands trigger external work. */
public final class ControlPlane {
    private final Ports.WorkflowLedger ledger;
    private final Ports.TaskSnapshotReader snapshots;
    private final Ports.TenantAuthz authz;
    private final Ports.ApprovalReader approvals;
    private final Ports.ReleasePolicy releasePolicy;
    private final Ports.TimeSource clock;
    private final Ports.EvidenceVerifier evidenceVerifier;
    private final AgentStore store;

    public ControlPlane(Ports.WorkflowLedger ledger, Ports.TaskSnapshotReader snapshots,
                        Ports.TenantAuthz authz, Ports.ApprovalReader approvals,
                        Ports.ReleasePolicy releasePolicy, Ports.TimeSource clock, AgentStore store,
                        Ports.EvidenceVerifier evidenceVerifier) {
        this.ledger=ledger; this.snapshots=snapshots; this.authz=authz;
        this.approvals=approvals; this.releasePolicy=releasePolicy; this.clock=clock; this.store=store;
        this.evidenceVerifier=java.util.Objects.requireNonNull(evidenceVerifier);
    }
    private static void require(boolean ok, String code) {
        if (!ok) throw new IllegalStateException(code);
    }
    private static void required(String s) { require(AgentStore.filled(s), "REQUIRED_FIELD_MISSING"); }
    private static boolean goodRef(String ref) { return AgentStore.filled(ref) && ref.startsWith("artifact://"); }
    private void authorize(Principal actor, String tenant, String scope) { authz.check(actor, tenant, scope); }

    public Workflow.View start(Principal actor, Start req) {
        required(req.tenantId()); required(req.workflowId()); required(req.taskSnapshotId());
        required(req.correlationId()); required(req.idempotencyKey());
        require(req.limits() != null && clock.now().isBefore(req.limits().deadline()), "TIME_BUDGET_EXHAUSTED");
        authorize(actor, req.tenantId(), "factory:start");
        var existing = ledger.byIdempotency(req.tenantId(), req.idempotencyKey());
        if (existing.isPresent()) {
            require(existing.get().requestFingerprint.equals(Workflow.fingerprint(req)), "IDEMPOTENCY_CONFLICT");
            return existing.get().view();
        }
        Snapshot snap = snapshots.readReady(req.tenantId(), req.taskSnapshotId());
        require(snap != null && req.tenantId().equals(snap.tenantId()) &&
            req.taskSnapshotId().equals(snap.taskSnapshotId()) && "READY".equals(snap.status()), "SNAPSHOT_NOT_READY");
        require(AgentStore.hash(snap.digest()) && goodRef(snap.evaluationPolicyRef()) &&
            goodRef(snap.datasetVersionRef()) && AgentStore.filled(snap.snapshotRevision()), "UNPINNED_SNAPSHOT");
        Workflow w = new Workflow(req,snap);
        w.startedAt = clock.now();
        w.state = Workflow.State.READY;
        w.audit.add(new Workflow.Audit(clock.now(),Workflow.State.DRAFT,Workflow.State.READY,null,w.correlationId));
        w.state = Workflow.State.BUILDING;
        w.audit.add(new Workflow.Audit(clock.now(),Workflow.State.READY,Workflow.State.BUILDING,null,w.correlationId));
        w.enqueue(Workflow.ActionType.BUILD, null, null);
        return ledger.open(w).view();
    }
    /** Trusted scheduler/reconciliation adapter terminates workflows over wallclock limit. */
    public int expireDueWorkflows() {
        int expired=0;
        for (Ports.Key key : ledger.activeKeys()) {
            boolean changed=ledger.transact(key.tenantId(),key.workflowId(),w -> {
                if (w.state==Workflow.State.BLOCKED || w.state==Workflow.State.RELEASED ||
                    w.state==Workflow.State.ROLLED_BACK || clock.now().isBefore(w.limits.deadline()))
                    return false;
                block(w,"TIME_BUDGET_EXHAUSTED","restart with authorized limits");
                return true;
            });
            if (changed) expired++;
        }
        return expired;
    }
    public Workflow.View get(Principal actor, String tenant, String workflowId) {
        authorize(actor,tenant,"factory:read");
        return ledger.get(tenant,workflowId).view();
    }

    private boolean sameEvent(Workflow w, Header h, Object event) {
        require(h != null && "0.1".equals(h.schemaVersion()) && AgentStore.filled(h.eventId()) &&
            AgentStore.filled(h.operationId()) && AgentStore.filled(h.correlationId()) &&
            h.occurredAt()!=null && h.tenantId().equals(w.tenantId) &&
            h.workflowId().equals(w.workflowId) && h.correlationId().equals(w.correlationId), "INVALID_EVENT_HEADER");
        String fingerprint = event.toString();
        String existing = w.inbox.get(h.eventId());
        if (existing != null) {
            require(existing.equals(fingerprint), "EVENT_ID_COLLISION");
            return true;
        }
        // Only a dispatch receipt may acknowledge a command.
        // Early or stale events are not recorded until the matching action was dispatched.
        return false;
    }
    private boolean expected(Workflow w, Header h, Workflow.State... stages) {
        boolean stateAllowed = false;
        for (Workflow.State s : stages) if (w.state == s) stateAllowed=true;
        if (!stateAllowed || !Objects.equals(w.pendingOperationId,h.operationId())) return false;
        // Early completion is retried by the transport; never acknowledge an unaccepted command.
        if (w.actions.stream().noneMatch(a -> a.operationId.equals(h.operationId()) && a.delivered))
            throw new IllegalStateException("EVENT_AWAITING_COMMAND_RECEIPT");
        return true;
    }
    private void block(Workflow w, String code, String action) {
        w.state=Workflow.State.BLOCKED; w.errorCode=code; w.requiredAction=action;
        w.pendingOperationId=null;
    }
    private boolean budgetOkay(Workflow w, BigDecimal increment) {
        if (increment == null || increment.signum()<0) {
            block(w,"INVALID_USAGE","investigate billing evidence"); return false;
        }
        w.spentUsd = w.spentUsd.add(increment);
        if (w.spentUsd.compareTo(w.limits.maxUsd()) > 0) {
            block(w,"SPEND_BUDGET_EXHAUSTED","raise budget with authorization"); return false;
        }
        if (!clock.now().isBefore(w.limits.deadline())) {
            block(w,"TIME_BUDGET_EXHAUSTED","start a new authorized workflow"); return false;
        }
        return true;
    }
    private void verifyEventActor(Principal actor, Header h, String scope) {
        require(h != null && AgentStore.filled(h.tenantId()), "INVALID_EVENT_HEADER");
        authorize(actor, h.tenantId(), scope);
    }

    public Workflow.View onBuild(Principal actor, BuildFinished event) {
        verifyEventActor(actor,event.header(),"factory:events:build");
        Header h=event.header();
        return ledger.transact(h.tenantId(),h.workflowId(),w -> {
            if (sameEvent(w,h,event) || !expected(w,h,Workflow.State.BUILDING)) return w.view();
            w.inbox.put(h.eventId(),event.toString());
            if (!clock.now().isBefore(w.limits.deadline())) {
                block(w,"TIME_BUDGET_EXHAUSTED","start a new authorized workflow");
            } else if (!event.success()) {
                block(w,AgentStore.filled(event.failureCode())?event.failureCode():"BUILD_FAILED","inspect build failure");
            } else if (!AgentStore.hash(event.specDigest()) || !goodRef(event.specRef()) ||
                       !AgentStore.hash(event.modelRouteDigest()) ||
                       event.toolDigests() == null || event.toolDigests().isEmpty() ||
                       event.toolDigests().values().stream().anyMatch(d -> !AgentStore.hash(d)) ||
                       !AgentStore.filled(event.agentId())) {
                block(w,"INVALID_AGENT_SPEC","rebuild with pinned artifacts");
            } else {
                w.agentId=event.agentId(); w.specRef=event.specRef(); w.specDigest=event.specDigest();
                w.baselineRef=event.specRef(); w.baselineDigest=event.specDigest();
                w.toolDigests=Map.copyOf(event.toolDigests());
                w.modelRouteDigest=event.modelRouteDigest(); w.a2aCardRef=event.a2aCardRef();
                w.state=Workflow.State.TESTING;
                w.enqueue(Workflow.ActionType.EVALUATE,w.specRef,w.specDigest);
            }
            return w.view();
        });
    }

    public Workflow.View onEvaluation(Principal actor, EvaluationFinished event) {
        verifyEventActor(actor,event.header(),"factory:events:evaluation");
        Header h=event.header();
        boolean[] processed={false};
        Workflow.View view = ledger.transact(h.tenantId(),h.workflowId(),w -> {
            if (sameEvent(w,h,event) || !expected(w,h,Workflow.State.TESTING,Workflow.State.RE_TESTING)) return w.view();
            processed[0]=true;
            w.inbox.put(h.eventId(),event.toString());
            if (!Objects.equals(w.specDigest,event.specDigest()) || event.evidence()==null ||
                !Objects.equals(event.specDigest(),event.evidence().specDigest()) ||
                !Objects.equals(event.evaluationRunId(),event.evidence().evaluationRunId())) {
                block(w,"SPEC_VERSION_MISMATCH","evaluate the pinned candidate"); return w.view();
            }
            if (!budgetOkay(w,event.spendUsd())) return w.view();
            AgentStore.Evidence e=event.evidence();
            try {
                evidenceVerifier.validate(w.tenantId,event.evaluationRunId(),event.specDigest(),e);
            } catch (RuntimeException invalidEvidence) {
                block(w,"UNTRUSTED_EVALUATION_EVIDENCE","obtain independently attested evaluator result");
                return w.view();
            }
            w.lastEvidence=e;
            if (e.safetyVeto()) {
                block(w,"SAFETY_HARD_VETO","security and risk review");
            } else if (!AgentStore.filled(e.holdoutEvidenceRef()) || !AgentStore.filled(e.datasetRef()) ||
                       !AgentStore.filled(e.traceRef()) || !e.independent()) {
                block(w,"INDEPENDENT_HOLDOUT_MISSING","obtain evaluator-owned sealed holdout evidence");
            } else if (!w.datasetRef.equals(e.datasetRef()) || !w.baselineDigest.equals(e.baselineDigest())) {
                block(w,"EVALUATION_VERSION_MISMATCH","repeat evaluation against pinned dataset and baseline");
            } else if (e.passed() && e.complete()) {
                AgentStore.Version candidate=store.registerCandidate(new AgentStore.Metadata(w.tenantId,w.agentId,
                    w.specRef,w.specDigest,w.toolDigests,w.modelRouteDigest,w.a2aCardRef,e),
                    "candidate:"+w.workflowId+":"+w.specDigest);
                w.candidateVersion=candidate.version();
                w.state=Workflow.State.VERIFIED;
                w.pendingOperationId=null;
            } else if (e.passed()) {
                block(w,"INCOMPLETE_RELEASE_EVIDENCE","complete required audit and tool-effect evidence");
            } else if (event.failureCode()!=null && Set.of("MISSING_CAPABILITY", "NO_APPROVED_CONNECTOR",
                    "UNAUTHORIZED_TOOL", "POLICY_INVALID", "SEALED_HOLDOUT_UNAVAILABLE",
                    "TOOL_EFFECT_UNVERIFIED").contains(event.failureCode())) {
                block(w,event.failureCode(),"resolve evaluator's non-repairable finding");
            } else if (w.repairs>=w.limits.maxRepairs()) {
                block(w,"MAX_REPAIR_ATTEMPTS","manual diagnosis required");
            } else {
                w.repairs++;
                w.state=Workflow.State.OPTIMIZING;
                w.enqueue(Workflow.ActionType.OPTIMIZE,w.specRef,w.specDigest);
            }
            return w.view();
        });
        if (processed[0] && view.state()==Workflow.State.VERIFIED && event.evidence()!=null &&
            event.evidence().risk()==AgentStore.Risk.LOW && releasePolicy.allowAutomaticLowRisk(view)) {
            return promote(h.tenantId(),h.workflowId(),"auto:"+event.evaluationRunId(),true);
        }
        return view;
    }

    public Workflow.View onOptimization(Principal actor, OptimizationFinished event) {
        verifyEventActor(actor,event.header(),"factory:events:optimization");
        Header h=event.header();
        return ledger.transact(h.tenantId(),h.workflowId(),w -> {
            if (sameEvent(w,h,event) || !expected(w,h,Workflow.State.OPTIMIZING)) return w.view();
            w.inbox.put(h.eventId(),event.toString());
            require(w.actions.stream().anyMatch(a -> a.operationId.equals(h.operationId()) &&
                a.type == Workflow.ActionType.OPTIMIZE), "UNEXPECTED_OPTIMIZER_EVENT");
            if (!Objects.equals(w.specDigest,event.baseSpecDigest())) {
                block(w,"OPTIMIZATION_BASE_MISMATCH","discard stale optimization");
            } else if (!budgetOkay(w,event.spendUsd())) {
                // Exhausted budgets must never trigger evaluation or release.
            } else if (!event.success()) {
                block(w,AgentStore.filled(event.failureCode())?event.failureCode():"OPTIMIZATION_FAILED","manual diagnosis");
            } else if (!AgentStore.hash(event.candidateSpecDigest()) ||
                       !goodRef(event.candidateSpecRef()) || event.candidateSpecDigest().equals(w.specDigest)) {
                block(w,"INVALID_OPTIMIZATION_CANDIDATE","require immutable new candidate version");
            } else {
                w.specRef=event.candidateSpecRef(); w.specDigest=event.candidateSpecDigest();
                w.lastEvidence=null; w.candidateVersion=0;
                w.state=Workflow.State.RE_TESTING;
                w.enqueue(Workflow.ActionType.EVALUATE,w.specRef,w.specDigest);
            }
            return w.view();
        });
    }

    /** Optional, separately authorized training command; never implicitly initiated by GEPARD. */
    public Workflow.View requestSoup(Principal actor, String tenant, String workflowId, String rightsRef) {
        return requestSoup(actor,tenant,workflowId,rightsRef,"training:"+workflowId+":"+rightsRef);
    }

    public Workflow.View requestSoup(Principal actor, String tenant, String workflowId,
                                     String rightsRef, String idempotencyKey) {
        authorize(actor,tenant,"factory:training");
        required(idempotencyKey);
        require(goodRef(rightsRef) && approvals.approved(tenant,workflowId,"training:approve"),"TRAINING_RIGHTS_OR_APPROVAL_MISSING");
        return ledger.transact(tenant,workflowId,w -> {
            if (Objects.equals(w.trainingIdempotencyKey,idempotencyKey) &&
                w.trainingIdempotencyKey != null) {
                require(Objects.equals(w.trainingRightsRef,rightsRef),"IDEMPOTENCY_CONFLICT");
                return w.view();
            }
            require(w.state==Workflow.State.VERIFIED, "TRAINING_REQUIRES_VERIFIED_BASELINE");
            require(w.trainingAttempts<1 && clock.now().isBefore(w.limits.deadline()),"TRAINING_BUDGET_EXHAUSTED");
            w.trainingIdempotencyKey=idempotencyKey;
            w.trainingRightsRef=rightsRef;
            w.trainingAttempts++;
            w.state=Workflow.State.TRAINING;
            w.enqueue(Workflow.ActionType.SOUP,rightsRef,w.specDigest);
            return w.view();
        });
    }

    /** Separately authorized Soup completion; never promotes without fresh independent evaluation. */
    public Workflow.View onSoup(Principal actor, SoupFinished event) {
        verifyEventActor(actor,event.header(),"factory:events:soup");
        Header h=event.header();
        return ledger.transact(h.tenantId(),h.workflowId(),w -> {
            if (sameEvent(w,h,event) || !expected(w,h,Workflow.State.TRAINING)) return w.view();
            require(w.actions.stream().anyMatch(a -> a.operationId.equals(h.operationId()) &&
                a.type==Workflow.ActionType.SOUP), "UNEXPECTED_SOUP_EVENT");
            w.inbox.put(h.eventId(),event.toString());
            if (!Objects.equals(w.specDigest,event.baseSpecDigest())) {
                block(w,"TRAINING_BASE_MISMATCH","discard stale training artifact");
            } else if (!budgetOkay(w,event.spendUsd())) {
                // Budget hard stop; no evaluation is scheduled.
            } else if (!event.success()) {
                block(w,AgentStore.filled(event.failureCode())?event.failureCode():"TRAINING_FAILED",
                    "review training results and data rights");
            } else if (!AgentStore.hash(event.candidateSpecDigest()) ||
                       !AgentStore.hash(event.modelRouteDigest()) ||
                       !goodRef(event.candidateSpecRef()) ||
                       event.candidateSpecDigest().equals(w.specDigest)) {
                block(w,"INVALID_TRAINING_CANDIDATE","pin new spec and model revision");
            } else {
                w.specRef=event.candidateSpecRef(); w.specDigest=event.candidateSpecDigest();
                w.modelRouteDigest=event.modelRouteDigest();
                w.lastEvidence=null; w.candidateVersion=0;
                w.state=Workflow.State.RE_TESTING;
                w.enqueue(Workflow.ActionType.EVALUATE,w.specRef,w.specDigest);
            }
            return w.view();
        });
    }

    public Workflow.View release(Principal actor, String tenant, String workflowId, String idempotencyKey) {
        authorize(actor,tenant,"factory:release"); required(idempotencyKey);
        require(approvals.approved(tenant,workflowId,"release:approve"),"HUMAN_APPROVAL_REQUIRED");
        return promote(tenant,workflowId,"manual:"+idempotencyKey,false);
    }
    private Workflow.View promote(String tenant, String id, String operation, boolean auto) {
        return ledger.transact(tenant,id,w -> {
            if (w.state==Workflow.State.RELEASED) return w.view();
            require(w.state==Workflow.State.VERIFIED && w.lastEvidence!=null && w.lastEvidence.complete(),"QUALITY_GATE_BLOCKED");
            require(Objects.equals(w.specDigest,w.lastEvidence.specDigest()) &&
                w.spentUsd.compareTo(w.limits.maxUsd())<=0 && clock.now().isBefore(w.limits.deadline()),"RELEASE_CONSTRAINT_FAILED");
            require(!auto || (w.lastEvidence.risk()==AgentStore.Risk.LOW && releasePolicy.allowAutomaticLowRisk(w.view())),
                "AUTO_PROMOTION_DENIED");
            Set<String> signedApprovals = auto ? Set.of() : Set.of("release:approve");
            AgentStore.Evidence e=w.lastEvidence;
            AgentStore.Metadata m=new AgentStore.Metadata(tenant,w.agentId,w.specRef,w.specDigest,
                w.toolDigests,w.modelRouteDigest,w.a2aCardRef,e);
            AgentStore.Version v=store.registerCandidate(m,"candidate:"+id+":"+w.specDigest);
            require(v.version()==w.candidateVersion, "CANDIDATE_VERSION_MISMATCH");
            AgentStore.Version released=store.promote(tenant,w.agentId,v.version(),operation,signedApprovals,auto);
            w.releasedVersion=released.version();
            w.state=Workflow.State.RELEASED;
            w.pendingOperationId=null;
            return w.view();
        });
    }
    public Workflow.View rollback(Principal actor, String tenant, String workflowId, String idempotencyKey) {
        authorize(actor,tenant,"factory:rollback"); required(idempotencyKey);
        require(approvals.approved(tenant,workflowId,"rollback:approve"),"ROLLBACK_APPROVAL_REQUIRED");
        return ledger.transact(tenant,workflowId,w -> {
            if (w.state==Workflow.State.ROLLED_BACK) return w.view();
            require(w.state==Workflow.State.RELEASED,"RELEASE_NOT_ACTIVE");
            store.rollback(tenant,w.agentId,w.releasedVersion,"rollback:"+idempotencyKey);
            w.state=Workflow.State.ROLLED_BACK;
            w.pendingOperationId=null;
            return w.view();
        });
    }
    public java.util.List<Workflow.Audit> audit(Principal actor, String tenant, String workflowId) {
        authorize(actor,tenant,"factory:read");
        return java.util.List.copyOf(ledger.get(tenant,workflowId).audit);
    }
    Ports.WorkflowLedger ledger() { return ledger; }
}
