"""Quality non-inferiority and cost-per-correct-task benchmark."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .primitives import InvalidEvidence

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
        if any(r.hard_veto for r in baseline):
            reasons.append("UNSAFE_BASELINE")
        if any(r.total_cost < 0 or r.latency_ms < 0 for r in baseline + candidate):
            raise InvalidEvidence("negative cost or latency")
        b_success = sum(r.success and not r.hard_veto for r in baseline)
        c_success = sum(r.success and not r.hard_veto for r in candidate)
        losses = sum(b.success and not b.hard_veto and (not c.success or c.hard_veto)
                     for b, c in zip(baseline, candidate))
        upper = _loss_upper_bound(losses, len(baseline), policy.alpha)
        if losses / len(baseline) > policy.max_quality_drop:
            reasons.append("OBSERVED_QUALITY_REGRESSION")
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
        elif any(x in reasons for x in ("MODEL_CAPABILITY_MISMATCH", "SAFETY_HARD_VETO", "UNSAFE_BASELINE", "OBSERVED_QUALITY_REGRESSION", "SAME_MODEL", "NO_PROVEN_COST_SAVINGS")):
            status = "FAILED"
        else:
            status = "INCONCLUSIVE"
        return BenchmarkResult(status, bc, cc, c_success/len(candidate)-b_success/len(baseline),
                               upper, tuple(reasons))
