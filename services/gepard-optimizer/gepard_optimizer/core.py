"""Typed optimizer port; deterministic fake backend until DSPy GEPA integration is proven."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable
import json


class OptimizerInputError(ValueError):
    pass


@dataclass(frozen=True)
class OptimizationRequest:
    tenant_id: str
    agent_spec_ref: str
    baseline_spec_ref: str
    existing_prompt: str
    allowed_surfaces: tuple[str, ...]
    tuning_dataset_refs: tuple[str, ...]
    validation_dataset_refs: tuple[str, ...]
    max_candidates: int = 3


@dataclass(frozen=True)
class CandidatePatch:
    tenant_id: str
    source_agent_spec_ref: str
    surface: str
    replacement: str
    patch_digest: str
    status: str = "REQUIRES_INDEPENDENT_EVALUATION"


class OptimizerAdapter:
    """Uses a backend on approved training material, not hidden Evaluation holdouts.

    An injected callable permits DSPy/GEPA integration later; by default this
    class performs a deterministic mock improvement, NOT actual GEPA training.
    """
    _SURFACES = frozenset({"system_prompt", "tool_description"})

    def __init__(self, backend: Callable[[str], str] | None = None):
        self._backend = backend or (lambda p: p + "\nVerify every mandatory tool effect before claiming completion.")
        self.backend_name = "injected" if backend else "deterministic_mock_not_gepa"

    def propose(self, request: OptimizationRequest) -> CandidatePatch:
        if not request.tenant_id or not request.agent_spec_ref or not request.baseline_spec_ref:
            raise OptimizerInputError("pinned tenant and AgentSpec versions required")
        if request.max_candidates < 1 or request.max_candidates > 10:
            raise OptimizerInputError("invalid bounded candidate budget")
        if not request.tuning_dataset_refs or not request.validation_dataset_refs:
            raise OptimizerInputError("separate tuning and validation references required")
        if any("holdout" in ref.lower() or "sealed" in ref.lower() for ref in request.tuning_dataset_refs + request.validation_dataset_refs):
            raise OptimizerInputError("holdout cannot be optimizer input")
        if len(request.allowed_surfaces) != 1 or request.allowed_surfaces[0] not in self._SURFACES:
            raise OptimizerInputError("optimizer cannot change code, MCP grants or policy")
        replacement = self._backend(request.existing_prompt)
        if not isinstance(replacement, str) or not replacement.strip() or replacement == request.existing_prompt:
            raise OptimizerInputError("optimizer did not produce a distinct valid candidate")
        payload = {"tenant_id": request.tenant_id, "source": request.agent_spec_ref,
                   "surface": request.allowed_surfaces[0], "replacement": replacement}
        digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return CandidatePatch(request.tenant_id, request.agent_spec_ref,
                              request.allowed_surfaces[0], replacement, digest)
