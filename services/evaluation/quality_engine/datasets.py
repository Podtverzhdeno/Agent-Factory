"""Tenant-scoped dataset classifications and in-process test vault."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal
from .primitives import AccessDenied, InvalidEvidence, Principal, digest

@dataclass(frozen=True)
class Case:
    case_id: str
    expected_artifact: dict[str, Any]
    required_tool_calls: tuple[str, ...] = ()
    required_effect_proofs: tuple[str, ...] = ()
    max_steps: int = 25
    input_ref: str = ""
    required_graph_events: tuple[str, ...] = ()
    required_memory_keys: tuple[str, ...] = ()


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
        self._datasets[key] = deepcopy(dataset)
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
        return deepcopy(ds)


