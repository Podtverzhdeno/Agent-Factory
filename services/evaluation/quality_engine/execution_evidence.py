"""Trust-boundary contract between a runtime observer and an independent grader."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .datasets import Case
from .evaluation import EvaluationRequest, ObservedRun
from .primitives import InvalidEvidence


@dataclass(frozen=True)
class PublicRunCase:
    case_id: str
    input_ref: str


@dataclass(frozen=True)
class EvidenceEnvelope:
    tenant_id: str
    agent_spec_digest: str
    dataset_version_ref: str
    case_id: str
    trace_ref: str
    observation: ObservedRun


class EvidenceCollector(Protocol):
    def collect(self, request: EvaluationRequest, case: PublicRunCase) -> Any: ...


class EvidenceVerifier(Protocol):
    def verify(self, attested: Any) -> EvidenceEnvelope: ...


def collect_observations(
    collector: EvidenceCollector, request: EvaluationRequest,
    cases: tuple[Case, ...], verifier: EvidenceVerifier | None,
    require_attestation: bool,
) -> tuple[ObservedRun, ...]:
    if require_attestation and verifier is None:
        raise InvalidEvidence("attestation is mandatory")
    observations = []
    for case in cases:
        value = collector.collect(request, PublicRunCase(case.case_id, case.input_ref))
        envelope = verifier.verify(value) if require_attestation and verifier else value
        if not isinstance(envelope, EvidenceEnvelope) or (
            envelope.tenant_id != request.tenant_id or
            envelope.agent_spec_digest != request.agent_spec_digest or
            envelope.dataset_version_ref != request.dataset_version_ref or
            envelope.case_id != case.case_id or
            envelope.observation.case_id != case.case_id or
            not envelope.trace_ref
        ):
            raise InvalidEvidence("untrusted execution evidence / pinned identity mismatch")
        observations.append(envelope.observation)
    return tuple(observations)
