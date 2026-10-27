"""Verify asymmetric Runtime audit signatures without holding signing secrets.

Runtime retains its Ed25519 private key. Evaluation receives tenant-scoped public
keys. Signatures complement authenticated transport and audited tool-effect proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from time import time
from typing import Callable
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .attestation import AttestedEvidence, canonical_evidence
from .execution_evidence import EvidenceEnvelope
from .primitives import InvalidEvidence


@dataclass(frozen=True)
class RuntimeAuditPublicKey:
    tenant_id: str
    public_key: Ed25519PublicKey
    revoked: bool = False
    valid_from: float | None = None
    valid_until: float | None = None


class Ed25519EvidenceVerifier:
    """Verifier-only adapter: no private key, no sign() method."""

    def __init__(self, keys: dict[str, RuntimeAuditPublicKey], *,
                 resolver: Callable[[str], RuntimeAuditPublicKey | None] | None = None,
                 clock: Callable[[], float] = time):
        if not keys or any(not kid or not item.tenant_id or not isinstance(item.public_key, Ed25519PublicKey)
                           for kid, item in keys.items()):
            raise ValueError("trusted per-tenant Runtime public keys required")
        self._keys = dict(keys)
        self._resolver = resolver or self._keys.get
        self._clock = clock

    def verify(self, claim: AttestedEvidence) -> EvidenceEnvelope:
        if not isinstance(claim, AttestedEvidence):
            raise InvalidEvidence("signed Runtime audit evidence required")
        entry = self._resolver(claim.key_id)
        if entry is None or entry.tenant_id != claim.envelope.tenant_id or entry.revoked:
            raise InvalidEvidence("revoked, unknown or cross-tenant Runtime signer")
        now = self._clock()
        if (not isfinite(now) or any(value is not None and not isfinite(value)
                                     for value in (entry.valid_from, entry.valid_until))):
            raise InvalidEvidence("invalid Runtime signer validity clock")
        if ((entry.valid_from is not None and now < entry.valid_from)
                or (entry.valid_until is not None and now >= entry.valid_until)):
            raise InvalidEvidence("Runtime signer key outside validity interval")
        try:
            signature = bytes.fromhex(claim.signature_hex)
            if len(signature) != 64:
                raise ValueError("invalid Ed25519 signature length")
            entry.public_key.verify(signature, canonical_evidence(claim.envelope))
        except (InvalidSignature, ValueError, TypeError) as exc:
            raise InvalidEvidence("Runtime audit signature verification failed") from exc
        return claim.envelope
