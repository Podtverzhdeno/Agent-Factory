"""Shared immutable identities and deterministic evidence hashing."""
from __future__ import annotations
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

def digest(obj: Any) -> str:
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class AccessDenied(PermissionError):
    pass


class InvalidEvidence(ValueError):
    pass


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    role: Literal["evaluation", "optimizer", "builder", "runtime"]


