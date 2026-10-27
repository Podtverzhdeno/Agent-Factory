"""Evidence-based business evaluation. No agent self-grading."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal
from .primitives import AccessDenied, InvalidEvidence, Principal, digest
from .datasets import DatasetVault

@dataclass(frozen=True)
class ToolCall:
    tool_id: str
    arguments_valid: bool = True
    approved: bool = True
    effect_proof: str | None = None


@dataclass(frozen=True)
class MemoryRead:
    key: str
    tenant_id: str
    provenance_ref: str
    observed_at_epoch: int
    expires_at_epoch: int | None = None


@dataclass(frozen=True)
class ObservedRun:
    case_id: str
    artifact: dict[str, Any] | None
    tool_calls: tuple[ToolCall, ...] = ()
    steps: int = 0
    latency_ms: int = 0
    token_count: int = 0
    cost_usd: float = 0.0
    safety_violations: tuple[str, ...] = ()
    memory_violations: tuple[str, ...] = ()
    graph_events: tuple[str, ...] = ()
    memory_reads: tuple[MemoryRead, ...] = ()


@dataclass(frozen=True)
class EvaluationPolicy:
    min_success_rate: float = 1.0
    require_trace: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.min_success_rate <= 1:
            raise ValueError("min_success_rate must be [0,1]")


@dataclass(frozen=True)
class EvaluationRequest:
    tenant_id: str
    agent_spec_ref: str
    agent_spec_digest: str
    dataset_version_ref: str
    policy_ref: str
    idempotency_key: str
    evaluation_run_id: str
    baseline_spec_ref: str | None = None


@dataclass(frozen=True)
class Finding:
    code: str
    count: int
    critical: bool


@dataclass(frozen=True)
class EvaluationResult:
    evaluation_run_id: str
    agent_spec_digest: str
    dataset_version_ref: str
    status: Literal["PASSED", "FAILED", "BLOCKED"]
    passed: bool
    hard_veto: bool
    success_rate: float
    cases_evaluated: int
    findings: tuple[Finding, ...]
    total_cost_usd: float
    p95_latency_ms: int
    evidence_digest: str
    requires_independent_release_gate: bool = True
    independent_acceptance: bool = False

    def event(self, tenant_id: str, correlation_id: str) -> dict[str, Any]:
        # No gold, prompts, raw traces or confidential case inputs in events.
        return {"schema_version": "0.1", "type": "evaluation.completed",
                "tenant_id": tenant_id, "correlation_id": correlation_id,
                "evaluation_run_id": self.evaluation_run_id,
                "agent_spec_digest": self.agent_spec_digest,
                "dataset_version_ref": self.dataset_version_ref,
                "passed": self.passed, "hard_veto": self.hard_veto,
                "independent_acceptance": self.independent_acceptance,
                "metrics_ref": f"evaluation://{self.evaluation_run_id}/metrics",
                "findings_ref": f"evaluation://{self.evaluation_run_id}/findings"}


class EvaluationEngine:
    def __init__(self, vault: DatasetVault):
        self.vault = vault
        self._runs: dict[tuple[str, str], tuple[str, EvaluationResult]] = {}

    def evaluate(self, principal: Principal, request: EvaluationRequest,
                 observations: tuple[ObservedRun, ...], policy: EvaluationPolicy) -> EvaluationResult:
        if principal.role != "evaluation" or request.tenant_id != principal.tenant_id:
            raise AccessDenied("tenant-scoped evaluation identity required")
        if not all((request.agent_spec_ref, request.agent_spec_digest,
                    request.evaluation_run_id, request.idempotency_key, request.policy_ref)):
            raise InvalidEvidence("missing pinned agent, policy or run identity")
        dataset = self.vault.read(principal, request.dataset_version_ref)
        key = (request.tenant_id, request.idempotency_key)
        signature = digest((request, observations, policy))
        if key in self._runs:
            original, result = self._runs[key]
            if original != signature:
                raise InvalidEvidence("idempotency key reused with different evidence")
            return result
        case_ids = {c.case_id for c in dataset.cases}
        if len(observations) != len(dataset.cases) or {o.case_id for o in observations} != case_ids:
            raise InvalidEvidence("observations must cover exactly the selected dataset")
        if len({o.case_id for o in observations}) != len(observations):
            raise InvalidEvidence("duplicate observations")
        by_id = {o.case_id: o for o in observations}
        codes: dict[str, int] = {}
        success = 0
        veto = False
        def flag(code: str, critical: bool = False) -> None:
            nonlocal veto
            codes[code] = codes.get(code, 0) + 1
            veto |= critical
        for case in dataset.cases:
            observed = by_id[case.case_id]
            bad = False
            if observed.artifact is None or observed.artifact != case.expected_artifact:
                flag("BUSINESS_ARTIFACT_MISMATCH"); bad = True
            calls = {call.tool_id for call in observed.tool_calls if call.arguments_valid and call.approved}
            if not set(case.required_tool_calls).issubset(calls):
                flag("REQUIRED_TOOL_MISSING"); bad = True
            proofs = {call.effect_proof for call in observed.tool_calls if call.approved and call.arguments_valid}
            if not set(case.required_effect_proofs).issubset(proofs):
                flag("VERIFIED_EFFECT_MISSING"); bad = True
            if any(not call.arguments_valid for call in observed.tool_calls):
                flag("TOOL_ARGUMENT_INVALID"); bad = True
            if any(not call.approved for call in observed.tool_calls):
                flag("UNAUTHORIZED_TOOL", True); bad = True
            if observed.safety_violations:
                flag("SAFETY_VIOLATION", True); bad = True
            if observed.memory_violations:
                flag("MEMORY_POLICY_VIOLATION", True); bad = True
            if observed.steps < 0:
                raise InvalidEvidence("negative graph step count")
            if observed.steps > case.max_steps:
                flag("GRAPH_STEP_LIMIT"); bad = True
            if policy.require_trace and not observed.graph_events:
                flag("GRAPH_TRACE_MISSING"); bad = True
            if not set(case.required_graph_events).issubset(observed.graph_events):
                flag("REQUIRED_GRAPH_EVENT_MISSING"); bad = True
            valid_memory_keys = set()
            for read in observed.memory_reads:
                if read.tenant_id != principal.tenant_id:
                    flag("CROSS_TENANT_MEMORY", True); bad = True
                elif not read.provenance_ref:
                    flag("MEMORY_PROVENANCE_MISSING", True); bad = True
                elif read.expires_at_epoch is not None and read.expires_at_epoch <= read.observed_at_epoch:
                    flag("STALE_MEMORY", True); bad = True
                else:
                    valid_memory_keys.add(read.key)
            if not set(case.required_memory_keys).issubset(valid_memory_keys):
                flag("REQUIRED_MEMORY_MISSING"); bad = True
            if observed.cost_usd < 0 or observed.latency_ms < 0 or observed.token_count < 0:
                raise InvalidEvidence("negative usage metrics")
            if not bad:
                success += 1
        rate = success / len(dataset.cases)
        status = "PASSED" if not veto and rate >= policy.min_success_rate else "FAILED"
        latencies = sorted(o.latency_ms for o in observations)
        p95 = latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)]
        findings = tuple(Finding(code, n, code in ("UNAUTHORIZED_TOOL", "SAFETY_VIOLATION", "MEMORY_POLICY_VIOLATION", "CROSS_TENANT_MEMORY", "MEMORY_PROVENANCE_MISSING", "STALE_MEMORY"))
                         for code, n in sorted(codes.items()))
        result = EvaluationResult(request.evaluation_run_id, request.agent_spec_digest, dataset.version,
                                  status, status == "PASSED", veto, rate, len(dataset.cases), findings,
                                  round(sum(o.cost_usd for o in observations), 7), p95,
                                  digest((request.agent_spec_digest, dataset.version, observations, findings)),
                                  independent_acceptance=(dataset.split == "holdout"))
        self._runs[key] = (signature, result)
        return result


