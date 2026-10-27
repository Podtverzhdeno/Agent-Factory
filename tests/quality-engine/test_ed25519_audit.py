from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from quality_engine.application import EvidenceEnvelope
from quality_engine.attestation import AttestedEvidence, canonical_evidence
from quality_engine.ed25519_audit import Ed25519EvidenceVerifier, RuntimeAuditPublicKey
from quality_engine.core import ObservedRun, InvalidEvidence


def make_claim(private, tenant="a"):
    envelope = EvidenceEnvelope(tenant, "spec-hash", "holdout-v1", "case-1", "trace://run-1",
                                ObservedRun("case-1", {"result": "correct"}))
    return AttestedEvidence(envelope, "audit-key-1", private.sign(canonical_evidence(envelope)).hex())


def test_evaluation_can_verify_without_private_signing_key():
    runtime_private = Ed25519PrivateKey.generate()
    evaluator = Ed25519EvidenceVerifier({
        "audit-key-1": RuntimeAuditPublicKey("a", runtime_private.public_key())})
    valid = make_claim(runtime_private)
    assert evaluator.verify(valid).tenant_id == "a"
    assert not hasattr(evaluator, "sign")


def test_signature_or_tenant_spoofing_is_blocked():
    key = Ed25519PrivateKey.generate()
    evaluator = Ed25519EvidenceVerifier({"audit-key-1": RuntimeAuditPublicKey("a", key.public_key())})
    valid = make_claim(key)
    for invalid in (replace(valid, envelope=replace(valid.envelope, tenant_id="b")),
                    replace(valid, envelope=replace(valid.envelope, trace_ref="trace://altered")),
                    replace(valid, signature_hex="ab" * 64),
                    replace(valid, signature_hex="zzzz")):
        with pytest.raises(InvalidEvidence):
            evaluator.verify(invalid)


def test_untrusted_runtime_signer_is_denied():
    trusted = Ed25519PrivateKey.generate()
    attacker = Ed25519PrivateKey.generate()
    evaluator = Ed25519EvidenceVerifier({"audit-key-1": RuntimeAuditPublicKey("a", trusted.public_key())})
    with pytest.raises(InvalidEvidence):
        evaluator.verify(make_claim(attacker))


def test_cross_tenant_key_reuse_is_denied_even_when_signature_valid():
    key = Ed25519PrivateKey.generate()
    evaluator = Ed25519EvidenceVerifier({"audit-key-1": RuntimeAuditPublicKey("a", key.public_key())})
    with pytest.raises(InvalidEvidence):
        evaluator.verify(make_claim(key, tenant="b"))


def test_signer_revocation_rechecked_at_verification_time():
    key = Ed25519PrivateKey.generate()
    active_keys = {"audit-key-1": RuntimeAuditPublicKey("a", key.public_key())}
    verifier = Ed25519EvidenceVerifier(active_keys, resolver=active_keys.get)
    signed = make_claim(key)
    assert verifier.verify(signed).tenant_id == "a"
    active_keys["audit-key-1"] = RuntimeAuditPublicKey("a", key.public_key(), revoked=True)
    with pytest.raises(InvalidEvidence, match="revoked"):
        verifier.verify(signed)


def test_expired_signer_is_denied_even_with_valid_signature():
    key = Ed25519PrivateKey.generate()
    verifier = Ed25519EvidenceVerifier({
        "audit-key-1": RuntimeAuditPublicKey("a", key.public_key(), valid_from=10, valid_until=20),
    }, clock=lambda: 25)
    with pytest.raises(InvalidEvidence, match="validity"):
        verifier.verify(make_claim(key))


def test_invalid_signer_clock_fails_closed():
    key = Ed25519PrivateKey.generate()
    verifier = Ed25519EvidenceVerifier({
        "audit-key-1": RuntimeAuditPublicKey("a", key.public_key(), valid_until=20),
    }, clock=lambda: float("nan"))
    with pytest.raises(InvalidEvidence, match="clock"):
        verifier.verify(make_claim(key))
