"""Authenticated Runtime audit envelope verifier.

HMAC is a practical integration seam for an independently configured service
identity secret, not a substitute for transport authorization or tool audit.
Canonical JSON binds tenant, AgentSpec, dataset, case, trace and observed effects.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json

from .application import EvidenceEnvelope
from .primitives import InvalidEvidence


@dataclass(frozen=True)
class AttestedEvidence:
    envelope: EvidenceEnvelope
    key_id: str
    signature_hex: str


def canonical_evidence(envelope: EvidenceEnvelope) -> bytes:
    from dataclasses import asdict
    payload = asdict(envelope)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


class HmacEvidenceVerifier:
    """Explicit test/integration adapter; secrets provisioned outside agent config."""

    def __init__(self, keys: dict[str, bytes]):
        if not keys or any(not key_id or len(key) < 32 for key_id, key in keys.items()):
            raise ValueError("key IDs and >=32-byte keys required")
        self._keys = dict(keys)

    def sign(self, envelope: EvidenceEnvelope, *, key_id: str) -> AttestedEvidence:
        key = self._keys.get(key_id)
        if key is None:
            raise InvalidEvidence("unrecognized audit signer")
        signature = hmac.new(key, canonical_evidence(envelope), hashlib.sha256).hexdigest()
        return AttestedEvidence(envelope, key_id, signature)

    def verify(self, value: AttestedEvidence) -> EvidenceEnvelope:
        key = self._keys.get(value.key_id)
        if key is None:
            raise InvalidEvidence("unrecognized audit signer")
        try:
            expected = hmac.new(key, canonical_evidence(value.envelope), hashlib.sha256).hexdigest()
        except (TypeError, ValueError) as exc:
            raise InvalidEvidence("noncanonical audit evidence") from exc
        if not hmac.compare_digest(expected, value.signature_hex):
            raise InvalidEvidence("invalid audit signature")
        return value.envelope
