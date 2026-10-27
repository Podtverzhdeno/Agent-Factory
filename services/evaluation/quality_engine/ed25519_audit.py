"""Verify asymmetric Runtime audit signatures without holding signing secrets.

Runtime retains its Ed25519 private key. Evaluation receives tenant-scoped public
keys. Signatures complement authenticated transport and audited tool-effect proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .attestation import AttestedEvidence, canonical_evidence
from .execution_evidence import EvidenceEnvelope
from .primitives import InvalidEvidence


@dataclass(frozen=True)
class RuntimeAuditPublicKey:
    tenant_id: str
    public_key: Ed25519PublicKey


class Ed25519EvidenceVerifier:
    """Verifier-only adapter: no private key, no sign() method."""

    def __init__(self, keys: dict[str, RuntimeAuditPublicKey]):
        if not keys or any(not kid or not item.tenant_id or not isinstance(item.public_key, Ed25519PublicKey)
                           for kid, item in keys.items()):
            raise ValueError("trusted per-tenant Runtime public keys required")
        self._keys = dict(keys)

    def verify(self, claim: AttestedEvidence) -> EvidenceEnvelope:
        if not isinstance(claim, AttestedEvidence):
            raise InvalidEvidence("signed Runtime audit evidence required")
        entry = self._keys.get(claim.key_id)
        if entry is None or entry.tenant_id != claim.envelope.tenant_id:
            raise InvalidEvidence("unknown or cross-tenant Runtime signer")
        try:
            signature = bytes.fromhex(claim.signature_hex)
            if len(signature) != 64:
                raise ValueError("invalid Ed25519 signature length")
            entry.public_key.verify(signature, canonical_evidence(claim.envelope))
        except (InvalidSignature, ValueError, TypeError) as exc:
            raise InvalidEvidence("Runtime audit signature verification failed") from exc
        return claim.envelope
