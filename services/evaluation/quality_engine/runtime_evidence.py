"""Authenticated HTTP adapter for Agent Runtime audit evidence.

Transport: configured trusted Runtime origin + mutually controlled credential.
Evidence: Ed25519-signed canonical JSON with a pinned tenant/runtime public key.
Important: a signed Runtime statement is NOT proof of an irreversible external
business effect; independent tool-effect/audit authority is still required.
"""
from __future__ import annotations

import base64
import json
from typing import Callable

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .application import EvidenceEnvelope, PublicRunCase
from .core import (
    InvalidEvidence, EvaluationRequest, MemoryRead, ObservedRun, ToolCall,
)


class RuntimeEvidenceUnavailable(RuntimeError):
    """Transient runtime failure; never contains secrets or raw payloads."""


class SignedRuntimeEvidenceCollector:
    def __init__(self, *, client: httpx.Client,
                 access_token: Callable[[str], str],
                 verify_key: Callable[[str], Ed25519PublicKey],
                 max_status_reads: int = 8):
        if not 1 <= max_status_reads <= 60:
            raise ValueError("bounded status reads required")
        if client.follow_redirects:
            raise ValueError("redirects must be disabled to prevent credential exfiltration")
        self.client = client
        self.access_token = access_token
        self.verify_key = verify_key
        self.max_status_reads = max_status_reads

    @staticmethod
    def _canonical(body: dict) -> bytes:
        return json.dumps(body, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")

    def collect(self, request: EvaluationRequest, case: PublicRunCase) -> EvidenceEnvelope:
        if not request.tenant_id or not case.case_id or not case.input_ref:
            raise InvalidEvidence("pinned public input reference required")
        token = self.access_token(request.tenant_id)
        if not token or "\r" in token or "\n" in token:
            raise InvalidEvidence("missing service credential")
        run_id = f"{request.evaluation_run_id}:{case.case_id}"
        headers = {"Authorization": f"Bearer {token}",
                   "X-Correlation-ID": request.evaluation_run_id}
        request_body = {
            "tenant_id": request.tenant_id,
            "run_id": run_id,
            "agent_spec_ref": request.agent_spec_ref,
            "agent_spec_digest": request.agent_spec_digest,
            "dataset_version_ref": request.dataset_version_ref,
            "request_ref": case.input_ref,
            "case_id": case.case_id,
            "idempotency_key": run_id,
        }
        try:
            initiated = self.client.post("/internal/agent-runs", json=request_body,
                                         headers=headers, timeout=15.0)
            initiated.raise_for_status()
            if initiated.status_code not in (200, 202):
                raise InvalidEvidence("unexpected Runtime scheduling result")
            acknowledgement = initiated.json()
            if acknowledgement.get("run_id") != run_id:
                raise InvalidEvidence("Runtime acknowledged wrong run")
            for _ in range(self.max_status_reads):
                response = self.client.get(
                    f"/internal/agent-runs/{run_id}", headers=headers, timeout=15.0)
                response.raise_for_status()
                body = response.json()
                if body.get("status") in ("FAILED", "BLOCKED", "CANCELLED"):
                    raise InvalidEvidence("Runtime execution blocked")
                if body.get("status") == "COMPLETED":
                    return self._decode_verified(request, case, run_id, body)
                if body.get("status") not in ("QUEUED", "RUNNING"):
                    raise InvalidEvidence("unknown Runtime state")
        except (httpx.TimeoutException, httpx.NetworkError,
                httpx.HTTPStatusError) as exc:
            # Do not log response/request headers or token.
            raise RuntimeEvidenceUnavailable("Runtime unavailable or rejected request") from None
        raise RuntimeEvidenceUnavailable("Runtime result not yet completed")

    def _decode_verified(self, request: EvaluationRequest, case: PublicRunCase,
                         run_id: str, body: dict) -> EvidenceEnvelope:
        signature = body.get("signature")
        if not isinstance(signature, str) or not signature:
            raise InvalidEvidence("unsigned Runtime evidence")
        unsigned = {k: v for k, v in body.items() if k != "signature"}
        try:
            encoded = base64.b64decode(signature, validate=True)
            public = self.verify_key(request.tenant_id)
            public.verify(encoded, self._canonical(unsigned))
        except (InvalidSignature, ValueError, TypeError, KeyError) as exc:
            raise InvalidEvidence("Runtime signature verification failed") from None
        expected = {
            "tenant_id": request.tenant_id,
            "run_id": run_id,
            "case_id": case.case_id,
            "agent_spec_digest": request.agent_spec_digest,
            "dataset_version_ref": request.dataset_version_ref,
            "status": "COMPLETED",
        }
        if any(unsigned.get(k) != v for k, v in expected.items()):
            raise InvalidEvidence("Runtime proof does not match pinned context")
        if not unsigned.get("trace_ref"):
            raise InvalidEvidence("missing independent trace reference")
        try:
            payload = unsigned["observation"]
            observed = ObservedRun(
                case_id=case.case_id,
                artifact=payload.get("artifact"),
                tool_calls=tuple(ToolCall(**c) for c in payload.get("tool_calls", [])),
                steps=int(payload.get("steps", 0)),
                latency_ms=int(payload.get("latency_ms", 0)),
                token_count=int(payload.get("token_count", 0)),
                cost_usd=float(payload.get("cost_usd", 0)),
                safety_violations=tuple(payload.get("safety_violations", [])),
                memory_violations=tuple(payload.get("memory_violations", [])),
                graph_events=tuple(payload.get("graph_events", [])),
                memory_reads=tuple(MemoryRead(**m) for m in payload.get("memory_reads", [])),
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            raise InvalidEvidence("invalid signed Runtime observation") from None
        return EvidenceEnvelope(request.tenant_id, request.agent_spec_digest,
                                request.dataset_version_ref, case.case_id,
                                unsigned["trace_ref"], observed)
