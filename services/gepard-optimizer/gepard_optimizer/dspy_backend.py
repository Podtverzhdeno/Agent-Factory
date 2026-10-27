"""Optional DSPy GEPA bridge. Requires dspy install and an approved ModelGateway LM.

The consumer constructs a DSPy program, a metric based on TRAIN/VALIDATION
samples (not hidden holdout), and tenant-scoped examples. The result is a
candidate program, never an approved AgentSpec or a production rollout.
"""
from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
from typing import Any


class GepaUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GepaExecution:
    candidate_program: Any
    status: str = "REQUIRES_INDEPENDENT_EVALUATION"
    backend: str = "dspy.GEPA"


class DspyGepaBackend:
    def compile(self, *, student: Any, metric: Any, trainset: list[Any],
                valset: list[Any], reflection_lm: Any, max_metric_calls: int = 40,
                optimize_tool_descriptions: bool = False,
                train_ref: str = "", validation_ref: str = "") -> GepaExecution:
        if not trainset or not valset or reflection_lm is None or not callable(metric):
            raise ValueError("approved train/validation data, metric and reflection LM required")
        try:
            signature(metric).bind(None, None, None, None, None)
        except (TypeError, ValueError) as exc:
            raise ValueError("DSPy GEPA metric must accept 5 arguments") from exc
        if not 1 <= max_metric_calls <= 250:
            raise ValueError("bounded metric-call budget required")
        if not train_ref or not validation_ref or train_ref == validation_ref:
            raise ValueError("distinct versioned train/validation references required")
        if any("holdout" in s.lower() or "sealed" in s.lower()
               for s in (train_ref, validation_ref)):
            raise ValueError("hidden acceptance data is prohibited in GEPA")
        try:
            import dspy
        except ImportError as exc:
            raise GepaUnavailableError("install approved DSPy/GEPA dependency to run optimization") from exc
        optimizer = dspy.GEPA(metric=metric, reflection_lm=reflection_lm,
                              max_metric_calls=max_metric_calls,
                              enable_tool_optimization=optimize_tool_descriptions,
                              track_stats=True)
        candidate = optimizer.compile(student, trainset=trainset, valset=valset)
        return GepaExecution(candidate)
