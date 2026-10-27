"""Authenticated read-only HTTP client for the proposed signed Runtime audit API.

Execution is triggered separately by the Orchestrator. No gold or confidential
correct answer is sent to Runtime. The consumer requires verifier validation
before scoring or releasing any candidate.
"""
from __future__ import annotations

from dataclasses import fields
from math import isfinite
from urllib.parse import quote
import json

import httpx

from .attestation import AttestedEvidence
from .evaluation import EvaluationRequest, MemoryRead, ObservedRun, ToolCall
from .execution_evidence import EvidenceEnvelope, PublicRunCase
from .primitives import InvalidEvidence
from .secure_urls import validated_service_url


def _exact(raw: object, required: set[str]) -> dict:
    if not isinstance(raw, dict) or set(raw) != required:
        raise InvalidEvidence("unexpected Runtime audit schema")
    return raw


def _str(raw: object) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > 8192:
        raise InvalidEvidence("invalid Runtime audit field")
    return raw


def _counter(raw: object) -> int:
    if type(raw) is not int or raw < 0:
        raise InvalidEvidence("invalid Runtime audit counter")
    return raw


def _strings(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or len(raw) > 1000:
        raise InvalidEvidence("invalid Runtime audit list")
    return tuple(_str(item) for item in raw)


def _tools(raw: object) -> tuple[ToolCall, ...]:
    if not isinstance(raw, list) or len(raw) > 200:
        raise InvalidEvidence("invalid tool audit records")
    out = []
    for item in raw:
        data = _exact(item, {"tool_id", "arguments_valid", "approved", "effect_proof"})
        if type(data["arguments_valid"]) is not bool or type(data["approved"]) is not bool:
            raise InvalidEvidence("invalid tool audit flags")
        proof = data["effect_proof"]
        out.append(ToolCall(_str(data["tool_id"]), data["arguments_valid"], data["approved"],
                            _str(proof) if proof is not None else None))
    return tuple(out)


def _memories(raw: object) -> tuple[MemoryRead, ...]:
    if not isinstance(raw, list) or len(raw) > 200:
        raise InvalidEvidence("invalid memory audit records")
    out = []
    for item in raw:
        data = _exact(item, {"key", "tenant_id", "provenance_ref",
                             "observed_at_epoch", "expires_at_epoch"})
        expires = data["expires_at_epoch"]
        if expires is not None and (type(expires) is not int or expires < 0):
            raise InvalidEvidence("invalid memory expiration")
        out.append(MemoryRead(_str(data["key"]), _str(data["tenant_id"]),
                              _str(data["provenance_ref"]),
                              _counter(data["observed_at_epoch"]), expires))
    return tuple(out)


def decode_attested_evidence(raw: object) -> AttestedEvidence:
    signed = _exact(raw, {"envelope", "key_id", "signature_hex"})
    envelope = _exact(signed["envelope"], {"tenant_id", "agent_spec_digest",
                        "dataset_version_ref", "case_id", "trace_ref", "observation", "evaluation_run_id"})
    observed = _exact(envelope["observation"], {field.name for field in fields(ObservedRun)})
    artifact = observed["artifact"]
    if artifact is not None and not isinstance(artifact, dict):
        raise InvalidEvidence("invalid structured business artifact")
    cost = observed["cost_usd"]
    if type(cost) not in (int, float) or not isfinite(cost) or cost < 0:
        raise InvalidEvidence("invalid Runtime cost")
    observation = ObservedRun(
        case_id=_str(observed["case_id"]), artifact=artifact,
        tool_calls=_tools(observed["tool_calls"]),
        steps=_counter(observed["steps"]), latency_ms=_counter(observed["latency_ms"]),
        token_count=_counter(observed["token_count"]), cost_usd=cost,
        safety_violations=_strings(observed["safety_violations"]),
        memory_violations=_strings(observed["memory_violations"]),
        graph_events=_strings(observed["graph_events"]),
        memory_reads=_memories(observed["memory_reads"]),
    )
    typed_envelope = EvidenceEnvelope(
        _str(envelope["tenant_id"]), _str(envelope["agent_spec_digest"]),
        _str(envelope["dataset_version_ref"]), _str(envelope["case_id"]),
        _str(envelope["trace_ref"]), observation,
        _str(envelope["evaluation_run_id"]),
    )
    signature = _str(signed["signature_hex"])
    if len(signature) != 128:
        raise InvalidEvidence("invalid Ed25519 signature envelope")
    return AttestedEvidence(typed_envelope, _str(signed["key_id"]), signature)


class RuntimeEvidenceHTTPCollector:
    """Retrieve an existing authorized Runtime run's signed audit record.

    End-to-end orchestration and Runtime producer belong to agents 01/04.
    """

    def __init__(self, *, base_url: str, service_token: str,
                 transport: httpx.BaseTransport | None = None,
                 timeout_seconds: float = 20, max_bytes: int = 1_048_576):
        base_url = validated_service_url(base_url, label="Runtime endpoint")
        if not service_token or not 0 < timeout_seconds <= 120 or not 1024 <= max_bytes <= 10_000_000:
            raise ValueError("bounded Runtime authentication configuration required")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), transport=transport, timeout=timeout_seconds,
            follow_redirects=False, headers={"Authorization": f"Bearer {service_token}"},
        )
        self._max_bytes = max_bytes

    def collect(self, request: EvaluationRequest, case: PublicRunCase) -> AttestedEvidence:
        if not case.case_id or not case.input_ref:
            raise InvalidEvidence("public evaluation input reference is required")
        run_id = f"{request.evaluation_run_id}:{case.case_id}"
        path = f"/internal/agent-runs/{quote(run_id, safe='')}/evaluation-evidence"
        try:
            with self._client.stream(
                "GET", path,
                params={"case_id": case.case_id, "tenant_id": request.tenant_id,
                        "agent_spec_digest": request.agent_spec_digest,
                        "dataset_version_ref": request.dataset_version_ref},
            ) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                byte_count = 0
                for part in response.iter_bytes():
                    byte_count += len(part)
                    if byte_count > self._max_bytes:
                        raise InvalidEvidence("Runtime audit exceeds configured size")
                    chunks.append(part)
            return decode_attested_evidence(json.loads(b"".join(chunks)))
        except (httpx.HTTPError, ValueError, TypeError, UnicodeError) as exc:
            raise InvalidEvidence("Runtime audit retrieval failed") from exc

    def close(self) -> None:
        self._client.close()
