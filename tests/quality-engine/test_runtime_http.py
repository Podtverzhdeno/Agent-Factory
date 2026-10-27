"""HTTP contract and signed Runtime audit negative tests (transport mocked)."""
from dataclasses import asdict

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from quality_engine.application import EvidenceEnvelope
from quality_engine.attestation import canonical_evidence
from quality_engine.core import EvaluationRequest, InvalidEvidence, ObservedRun
from quality_engine.ed25519_audit import Ed25519EvidenceVerifier, RuntimeAuditPublicKey
from quality_engine.execution_evidence import PublicRunCase
from quality_engine.runtime_http import RuntimeEvidenceHTTPCollector


def _request():
    return EvaluationRequest("a", "spec", "digest", "holdout-v1", "policy", "idem", "eval")


def _signed(private, *, tenant="a", invalid_counter=False):
    env = EvidenceEnvelope(
        tenant, "digest", "holdout-v1", "case1", "trace://run",
        ObservedRun("case1", {"done": True}, graph_events=("final",)))
    result = {"envelope": asdict(env), "key_id": "runtime-v1",
              "signature_hex": private.sign(canonical_evidence(env)).hex()}
    if invalid_counter:
        result["envelope"]["observation"]["steps"] = "wrong"
    return result


def test_runtime_http_provenance_and_no_gold_leak():
    signer = Ed25519PrivateKey.generate()
    calls = []
    collector = RuntimeEvidenceHTTPCollector(
        base_url="https://runtime.example", service_token="test-token",
        transport=httpx.MockTransport(lambda req: (
            calls.append(req), httpx.Response(200, json=_signed(signer)))[1]),
    )
    try:
        attested = collector.collect(_request(), PublicRunCase("case1", "artifact://public"))
    finally:
        collector.close()
    verifier = Ed25519EvidenceVerifier({
        "runtime-v1": RuntimeAuditPublicKey("a", signer.public_key())})
    assert verifier.verify(attested).observation.artifact == {"done": True}
    assert calls[0].headers["Authorization"] == "Bearer test-token"
    assert calls[0].url.params["case_id"] == "case1"
    assert "input_ref" not in calls[0].url.params
    assert "done" not in str(calls[0].url)


@pytest.mark.parametrize("mode", ["forbidden", "invalid_usage", "unsigned", "garbage", "huge"])
def test_malformed_runtime_evidence_fails_closed(mode):
    signer = Ed25519PrivateKey.generate()
    def handler(request):
        if mode == "forbidden":
            return httpx.Response(403)
        if mode == "invalid_usage":
            return httpx.Response(200, json=_signed(signer, invalid_counter=True))
        if mode == "unsigned":
            return httpx.Response(200, json={"answer": "done"})
        if mode == "garbage":
            return httpx.Response(200, content=b"bad-json")
        return httpx.Response(200, content=b"X" * 100_000)
    collector = RuntimeEvidenceHTTPCollector(
        base_url="https://runtime.example", service_token="secret",
        transport=httpx.MockTransport(handler), max_bytes=4096,
    )
    try:
        with pytest.raises(InvalidEvidence):
            collector.collect(_request(), PublicRunCase("case1", "artifact://public"))
    finally:
        collector.close()


def test_modified_signature_or_cross_tenant_signed_result_denied():
    signer = Ed25519PrivateKey.generate()
    verifier = Ed25519EvidenceVerifier({
        "runtime-v1": RuntimeAuditPublicKey("a", signer.public_key())})
    for mode in ("modified", "foreign"):
        data = _signed(signer, tenant="other" if mode == "foreign" else "a")
        if mode == "modified":
            data["envelope"]["trace_ref"] = "tampered"
        collector = RuntimeEvidenceHTTPCollector(
            base_url="https://runtime.example", service_token="secret",
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=data)),
        )
        try:
            with pytest.raises(InvalidEvidence):
                verifier.verify(collector.collect(_request(), PublicRunCase("case1", "artifact://public")))
        finally:
            collector.close()


def test_runtime_client_requires_tls():
    with pytest.raises(ValueError):
        RuntimeEvidenceHTTPCollector(base_url="http://runtime.example", service_token="secret")
