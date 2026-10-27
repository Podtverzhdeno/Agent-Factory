"""Restricted, signed Runtime-to-Evaluation evidence producer (candidate).

Only the trusted Runtime and validated ToolGateway can populate observations.
No caller is allowed to supply an artifact or a fabricated tool-effect proof.
The in-memory store is a sandbox adapter, NOT a production audit ledger.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote

from agent_builder import AgentSpec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .core import Runtime, RuntimeDenied
from .verified_tools import VerifiedToolGateway

_ID = re.compile(r"[A-Za-z0-9_.-]{1,120}\Z")
_MAX_AUDIT_BYTES = 65536


@dataclass(frozen=True)
class VerifiedExecution:
    tool_id: str
    artifact: dict
    effect_proof: str | None


class EvidenceRecordingGateway(VerifiedToolGateway):
    """Record only *successful*, post-schema-validation gateway calls."""

    def __init__(self, tools, ledger, *, policies, timeout_seconds: float = 15.0):
        super().__init__(tools, ledger, policies=policies, timeout_seconds=timeout_seconds)
        self._observed: dict[tuple[str, str], list[VerifiedExecution]] = {}

    async def execute(self, spec, binding, *, args: dict, run_id: str, step: int):
        result, effect_key = await super().execute(
            spec, binding, args=args, run_id=run_id, step=step)
        proof = effect_key if any(e != "read" for e in binding.side_effects) else None
        self._observed.setdefault((spec.tenant_id, run_id), []).append(
            VerifiedExecution(binding.tool_id, dict(result), proof))
        return result, effect_key

    def take_evidence(self, tenant_id: str, run_id: str) -> tuple[VerifiedExecution, ...]:
        return tuple(self._observed.pop((tenant_id, run_id), ()))


class SignedRuntimeAudit:
    """Produce Evaluation's canonical Ed25519 audit schema from a *real* run.

    All IDs are supplied by an authenticated Orchestrator job. The service
    records a signed audit *after* Runtime returns; a GET never executes work.
    """

    def __init__(self, runtime: Runtime, spec: AgentSpec, *,
                 private_key: Ed25519PrivateKey, key_id: str):
        if not isinstance(runtime.gateway, EvidenceRecordingGateway):
            raise TypeError("trusted recording ToolGateway required")
        if not isinstance(private_key, Ed25519PrivateKey) or not key_id or len(key_id) > 128:
            raise ValueError("KMS-provisioned Ed25519 signer and key id required")
        if not spec.verify_digest() or spec.artifact_digest not in runtime.approved_spec_digests:
            raise ValueError("only a pinned immutable AgentSpec may produce audit evidence")
        self.runtime = runtime
        self._gateway = runtime.gateway
        self.spec = spec
        self._private_key = private_key
        self._key_id = key_id
        self._records: dict[tuple[str, str], dict] = {}
        self._requests: dict[tuple[str, str], str] = {}

    async def run_public_case(self, *, tenant_id: str, evaluation_run_id: str,
                              case_id: str, dataset_version_ref: str,
                              request: str) -> dict:
        if tenant_id != self.spec.tenant_id:
            raise RuntimeDenied("AUDIT_TENANT_DENIED")
        if not all(_ID.fullmatch(x) for x in (evaluation_run_id, case_id)):
            raise RuntimeDenied("INVALID_AUDIT_IDENTITY")
        if not isinstance(dataset_version_ref, str) or not (1 <= len(dataset_version_ref) <= 256):
            raise RuntimeDenied("INVALID_DATASET_VERSION")
        if not isinstance(request, str) or not request:
            raise RuntimeDenied("INVALID_AUDIT_REQUEST")
        run_id = f"{evaluation_run_id}:{case_id}"
        if len("eval:" + run_id) > 128:
            raise RuntimeDenied("INVALID_AUDIT_IDENTITY")
        key = (tenant_id, run_id)
        request_fingerprint = json.dumps(
            {"request": request, "dataset_version_ref": dataset_version_ref},
            sort_keys=True, separators=(",", ":"))
        if key in self._records:
            # Replays must be byte-for-byte the same job, not simply reuse IDs.
            if self._requests[key] != request_fingerprint:
                raise RuntimeDenied("AUDIT_IDEMPOTENCY_CONFLICT")
            return self._records[key]
        began = time.monotonic()
        result = await self.runtime.run(
            self.spec, tenant_id=tenant_id, run_id=run_id,
            thread_id=run_id, request=request, trace_id="eval:" + run_id)
        events = self._gateway.take_evidence(tenant_id, run_id)
        if len(events) != len(result.tool_effect_refs):
            raise RuntimeDenied("AUDIT_TOOL_EVIDENCE_MISMATCH")
        completed = result.status == "COMPLETED"
        observation = {
            "case_id": case_id,
            # Authoritative tool response, never the assistant's claimed answer.
            "artifact": events[-1].artifact if completed and events else None,
            "tool_calls": [
                {"tool_id": item.tool_id, "arguments_valid": True,
                 "approved": True, "effect_proof": item.effect_proof}
                for item in events
            ],
            "steps": result.steps,
            "latency_ms": max(0, int((time.monotonic() - began) * 1000)),
            "token_count": 0,  # Provider tokens unobserved; don't invent them.
            "cost_usd": result.cost_usd,
            "safety_violations": [result.error_code or "RUN_BLOCKED"] if not completed else [],
            "memory_violations": [],
            "graph_events": ["final" if completed else "blocked"],
            "memory_reads": [],
        }
        envelope = {
            "tenant_id": tenant_id,
            "agent_spec_digest": self.spec.artifact_digest,
            "dataset_version_ref": dataset_version_ref,
            "case_id": case_id,
            "trace_ref": "trace://eval/" + run_id,
            "observation": observation,
            "evaluation_run_id": evaluation_run_id,
        }
        canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                               allow_nan=False).encode("utf-8")
        if len(canonical) > _MAX_AUDIT_BYTES:
            raise RuntimeDenied("AUDIT_TOO_LARGE")
        signed = {"envelope": envelope, "key_id": self._key_id,
                  "signature_hex": self._private_key.sign(canonical).hex()}
        self._records[key] = signed
        self._requests[key] = request_fingerprint
        return signed

    def lookup(self, tenant_id: str, run_id: str) -> dict | None:
        return self._records.get((tenant_id, run_id))


class RuntimeAuditReadAPI:
    """Private read-only ASGI API matching Quality's HTTP collector.

    An identity resolver must be service-owned; client-supplied tenant headers
    or query fields never confer authority. No writes or execution over HTTP.
    """

    def __init__(self, audit: SignedRuntimeAudit, *, authenticate):
        self._audit = audit
        self._authenticate = authenticate

    @staticmethod
    async def _respond(send, status: int, body: dict) -> None:
        encoded = json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"),
                                (b"cache-control", b"no-store"),
                                (b"content-length", str(len(encoded)).encode())]})
        await send({"type": "http.response.body", "body": encoded})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            raise RuntimeDenied("AUDIT_HTTP_ONLY")
        if scope.get("method") != "GET":
            await self._respond(send, 405, {"error": "method_not_allowed"})
            return
        headers = [v for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
        if len(headers) != 1 or not headers[0].startswith(b"Bearer ") or len(headers[0]) > 4103:
            await self._respond(send, 401, {"error": "unauthorized"})
            return
        try:
            token = headers[0][7:].decode("ascii")
            tenant_id = self._authenticate(token) if token else None
        except Exception:  # noqa: BLE001 - auth failures must deny and not leak secrets.
            tenant_id = None
        if not isinstance(tenant_id, str) or not tenant_id:
            await self._respond(send, 401, {"error": "unauthorized"})
            return
        path = unquote(scope.get("path", ""))
        prefix = "/internal/agent-runs/"
        suffix = "/evaluation-evidence"
        if not path.startswith(prefix) or not path.endswith(suffix):
            await self._respond(send, 404, {"error": "not_found"})
            return
        run_id = path[len(prefix):-len(suffix)]
        if run_id.count(":") != 1 or any(not _ID.fullmatch(s) for s in run_id.split(":")):
            await self._respond(send, 404, {"error": "not_found"})
            return
        params = parse_qs(scope.get("query_string", b"").decode("ascii", errors="ignore"))
        required = {"case_id", "tenant_id", "agent_spec_digest", "dataset_version_ref"}
        if set(params) != required or any(len(v) != 1 for v in params.values()):
            await self._respond(send, 400, {"error": "invalid_query"})
            return
        value = self._audit.lookup(tenant_id, run_id)
        if value is None:
            await self._respond(send, 404, {"error": "not_found"})
            return
        envelope = value["envelope"]
        if (envelope is None or params["tenant_id"][0] != tenant_id
                or params["case_id"][0] != envelope["case_id"]
                or params["agent_spec_digest"][0] != envelope["agent_spec_digest"]
                or params["dataset_version_ref"][0] != envelope["dataset_version_ref"]
                or run_id != envelope["evaluation_run_id"] + ":" + envelope["case_id"]):
            await self._respond(send, 404, {"error": "not_found"})
            return
        await self._respond(send, 200, value)
