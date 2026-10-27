"""AES-256-GCM authenticated encryption of private evaluator gold cases.

Tenant-scoped keys must come from a trusted vault/KMS. Associated data binds
ciphertext to tenant, dataset version and case ID, preventing record swaps.
"""
from __future__ import annotations

import base64
import os
from typing import Callable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from .primitives import InvalidEvidence


class AesGcmGoldCipher:
    PREFIX = "enc:aes256gcm:v1:"

    def __init__(self, key_provider: Callable[[str], bytes]):
        self._provider = key_provider

    def _key(self, tenant: str) -> bytes:
        key = self._provider(tenant)
        if not isinstance(key, bytes) or len(key) != 32:
            raise InvalidEvidence("tenant encryption key unavailable")
        return key

    @staticmethod
    def _aad(tenant: str, version: str, case_id: str) -> bytes:
        return f"{tenant}\x00{version}\x00{case_id}".encode("utf-8")

    def seal(self, *, tenant: str, version: str, case_id: str, plaintext: str) -> str:
        nonce = os.urandom(12)
        encrypted = AESGCM(self._key(tenant)).encrypt(
            nonce, plaintext.encode("utf-8"), self._aad(tenant, version, case_id))
        return self.PREFIX + base64.b64encode(nonce + encrypted).decode("ascii")

    def open(self, *, tenant: str, version: str, case_id: str, ciphertext: str) -> str:
        if not ciphertext.startswith(self.PREFIX):
            raise InvalidEvidence("gold artifact is not encrypted")
        try:
            decoded = base64.b64decode(ciphertext[len(self.PREFIX):], validate=True)
            if len(decoded) < 29:
                raise ValueError("invalid AEAD envelope")
            clear = AESGCM(self._key(tenant)).decrypt(
                decoded[:12], decoded[12:], self._aad(tenant, version, case_id))
            return clear.decode("utf-8")
        except (InvalidTag, ValueError, UnicodeError) as exc:
            raise InvalidEvidence("gold decryption/integrity failure") from exc
