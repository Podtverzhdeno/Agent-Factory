"""Quality engine: deterministic business evidence, sealed gold and price-quality decisions.

Component implementation only. No production API/authentication, Kafka or real LiteLLM
connection is claimed. External principals must be injected by trusted infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal
import json


def digest(obj: Any) -> str:
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class AccessDenied(PermissionError):
    pass


class InvalidEvidence(ValueError):
    pass


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    role: Literal["evaluation", "optimizer", "builder", "runtime"]


@dataclass(frozen=True)
class Case:
    case_id: str
    expected_artifact: dict[str, Any]
    required_tool_calls: tuple[str, ...] = ()
    required_effect_proofs: tuple[str, ...] = ()
    max_steps: int = 25


@dataclass(frozen=True)
class Dataset:
    tenant_id: str
    version: str
    split: Literal["tune", "validation", "holdout"]
    cases: tuple[Case, ...]

    def __post_init__(self) -> None:
        if not self.version or not self.tenant_id or not self.cases:
            raise InvalidEvidence("dataset requires tenant, version and cases")
        if len(set(c.case_id for c in self.cases)) != len(self.cases):
            raise InvalidEvidence("duplicate case IDs")


class DatasetVault:
    """No raw hidden case retrieval except by a tenant-scoped evaluator identity."""
    def __init__(self) -> None:
        self._datasets: dict[tuple[str, str], Dataset] = {}
        self._fingerprints: dict[str, dict[str, set[str]]] = {}

    def register(self, principal: Principal, dataset: Dataset) -> None:
        if principal.role != "evaluation" or principal.tenant_id != dataset.tenant_id:
            raise AccessDenied("evaluation owner of tenant required")
        key = (dataset.tenant_id, dataset.version)
        if key in self._datasets:
            raise InvalidEvidence("dataset version immutable")
        signatures = {digest({"artifact": c.expected_artifact, "tool": c.required_tool_calls,
                             "effects": c.required_effect_proofs}) for c in dataset.cases}
        used = self._fingerprints.setdefault(dataset.tenant_id, {})
        for split, existing in used.items():
            if (dataset.split == "holdout") != (split == "holdout") and (existing & signatures):
                raise InvalidEvidence("gold answer contamination across holdout boundary")
        self._datasets[key] = dataset
        used.setdefault(dataset.split, set()).update(signatures)

    def read(self, principal: Principal, version: str) -> Dataset:
        key = (principal.tenant_id, version)
        if key not in self._datasets:
            raise AccessDenied("dataset not accessible")
        ds = self._datasets[key]
        if ds.split == "holdout" and principal.role != "evaluation":
            raise AccessDenied("sealed holdout is evaluator-only")
        if ds.split == "validation" and principal.role != "evaluation":
            raise AccessDenied("independent validation is evaluator-only")
        if principal.role not in ("evaluation", "optimizer"):
            raise AccessDenied("dataset is not exposed to builder/runtime")
        return ds


@dataclass(frozen=True)
class ToolCall:
    tool_id: str
    arguments_valid: bool = True
    approved: bool = True
    effect_proof: str | None = None


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

    def event(self, tenant_id: str, correlation_id: str) -> dict[str, Any]:
        # No gold, prompts, raw traces or confidential case inputs in events.
        return {"schema_version": "0.1", "type": "evaluation.completed",
                "tenant_id": tenant_id, "correlation_id": correlation_id,
                "evaluation_run_id": self.evaluation_run_id,
                "agent_spec_digest": self.agent_spec_digest,
                "dataset_version_ref": self.dataset_version_ref,
                "passed": self.passed, "hard_veto": self.hard_veto,
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
            if observed.steps > case.max_steps:
                flag("GRAPH_STEP_LIMIT"); bad = True
            if policy.require_trace and not observed.graph_events:
                flag("GRAPH_TRACE_MISSING"); bad = True
            if observed.cost_usd < 0 or observed.latency_ms < 0 or observed.token_count < 0:
                raise InvalidEvidence("negative usage metrics")
            if not bad:
                success += 1
        rate = success / len(dataset.cases)
        status = "PASSED" if not veto and rate >= policy.min_success_rate else "FAILED"
        latencies = sorted(o.latency_ms for o in observations)
        p95 = latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)]
        findings = tuple(Finding(code, n, code in ("UNAUTHORIZED_TOOL", "SAFETY_VIOLATION", "MEMORY_POLICY_VIOLATION"))
                         for code, n in sorted(codes.items()))
        result = EvaluationResult(request.evaluation_run_id, request.agent_spec_digest, dataset.version,
                                  status, status == "PASSED", veto, rate, len(dataset.cases), findings,
                                  round(sum(o.cost_usd for o in observations), 7), p95,
                                  digest((request.agent_spec_digest, dataset.version, observations, findings)))
        self._runs[key] = (signature, result)
        return result


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    supports_tools: bool
    supports_json: bool
    context_tokens: int
    processing_region: str


@dataclass(frozen=True)
class ModelRun:
    case_id: str
    success: bool
    hard_veto: bool
    model_cost_usd: float
    retry_cost_usd: float = 0.0
    tool_cost_usd: float = 0.0
    fallback_cost_usd: float = 0.0
    latency_ms: int = 0

    @property
    def total_cost(self) -> float:
        return self.model_cost_usd + self.retry_cost_usd + self.tool_cost_usd + self.fallback_cost_usd


@dataclass(frozen=True)
class BenchmarkPolicy:
    min_cases: int = 40
    max_quality_drop: float = 0.05
    min_savings_fraction: float = 0.1
    required_context_tokens: int = 1000
    region: str = "EU"
    needs_tools: bool = True
    needs_json: bool = True
    alpha: float = 0.05


@dataclass(frozen=True)
class BenchmarkResult:
    status: Literal["PASSED", "FAILED", "INCONCLUSIVE"]
    baseline_cost_per_success: float | None
    candidate_cost_per_success: float | None
    observed_success_delta: float
    loss_upper_bound: float
    reasons: tuple[str, ...]
    requires_independent_release_gate: bool = True


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if p >= 1:
        return 1.0 if k >= n else 0.0
    if p <= 0:
        return 1.0
    term = (1-p)**n
    total = term
    for i in range(1, k+1):
        term *= (n-i+1)*p/(i*(1-p))
        total += term
    return total


def _loss_upper_bound(losses: int, n: int, alpha: float) -> float:
    if losses == n:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(65):
        mid = (low+high)/2
        if _binomial_cdf(losses, n, mid) > alpha:
            low = mid
        else:
            high = mid
    return high


class BenchmarkEngine:
    def compare(self, baseline_model: ModelProfile, candidate_model: ModelProfile,
                baseline: tuple[ModelRun, ...], candidate: tuple[ModelRun, ...],
                policy: BenchmarkPolicy) -> BenchmarkResult:
        if not 0 < policy.alpha < 1 or not 0 <= policy.max_quality_drop < 1 or not 0 <= policy.min_savings_fraction < 1:
            raise ValueError("invalid benchmark policy")
        if not baseline or not candidate or len(baseline) != len(candidate):
            raise InvalidEvidence("paired model cases required")
        bid, cid = [r.case_id for r in baseline], [r.case_id for r in candidate]
        if bid != cid or len(set(bid)) != len(bid):
            raise InvalidEvidence("baseline/candidate must be aligned, unique and in same order")
        reasons: list[str] = []
        if baseline_model.model_id == candidate_model.model_id:
            reasons.append("SAME_MODEL")
        if (policy.needs_tools and not candidate_model.supports_tools or
            policy.needs_json and not candidate_model.supports_json or
            candidate_model.context_tokens < policy.required_context_tokens or
            candidate_model.processing_region != policy.region):
            reasons.append("MODEL_CAPABILITY_MISMATCH")
        if any(r.hard_veto for r in candidate):
            reasons.append("SAFETY_HARD_VETO")
        if any(r.total_cost < 0 or r.latency_ms < 0 for r in baseline + candidate):
            raise InvalidEvidence("negative cost or latency")
        b_success = sum(r.success and not r.hard_veto for r in baseline)
        c_success = sum(r.success and not r.hard_veto for r in candidate)
        losses = sum(b.success and not b.hard_veto and (not c.success or c.hard_veto)
                     for b, c in zip(baseline, candidate))
        upper = _loss_upper_bound(losses, len(baseline), policy.alpha)
        if upper > policy.max_quality_drop:
            reasons.append("QUALITY_NONINFERIORITY_NOT_PROVEN")
        bc = sum(r.total_cost for r in baseline) / b_success if b_success else None
        cc = sum(r.total_cost for r in candidate) / c_success if c_success else None
        if bc is None or cc is None:
            reasons.append("SUCCESS_DENOMINATOR_ZERO")
        elif not cc <= bc * (1 - policy.min_savings_fraction):
            reasons.append("NO_PROVEN_COST_SAVINGS")
        if len(baseline) < policy.min_cases:
            reasons.append("INSUFFICIENT_CASES")
        if not reasons:
            status: Literal["PASSED", "FAILED", "INCONCLUSIVE"] = "PASSED"
        elif any(x in reasons for x in ("MODEL_CAPABILITY_MISMATCH", "SAFETY_HARD_VETO", "SAME_MODEL", "NO_PROVEN_COST_SAVINGS")):
            status = "FAILED"
        else:
            status = "INCONCLUSIVE"
        return BenchmarkResult(status, bc, cc, c_success/len(candidate)-b_success/len(baseline),
                               upper, tuple(reasons))
