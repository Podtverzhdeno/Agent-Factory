"""SQLAlchemy-backed tenant-isolated encrypted gold dataset store.

Production DSN: postgresql+psycopg://... (driver/DB configured by platform).
SQLite is supported ONLY for isolated component tests. The encryption key is
injected from a secret manager, never persisted with ciphertext or logged.
Application-level RBAC complements (does not replace) service IAM and DB ACL.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import (Column, LargeBinary, MetaData, String, Table,
                        create_engine, insert, select)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .datasets import Case, Dataset
from .primitives import AccessDenied, InvalidEvidence, Principal, digest


_METADATA = MetaData()
_DATASETS = Table(
    "evaluation_datasets", _METADATA,
    Column("tenant_id", String(160), primary_key=True),
    Column("version", String(160), primary_key=True),
    Column("split", String(32), nullable=False),
    Column("payload", LargeBinary, nullable=False),
    Column("payload_sha256", String(64), nullable=False),
)
# Uniqueness across ANY split ensures even concurrent train/holdout registration
# cannot silently recycle the same source reference under a different label.
_FINGERPRINTS = Table(
    "evaluation_case_sources", _METADATA,
    Column("tenant_id", String(160), primary_key=True),
    Column("fingerprint", String(64), primary_key=True),
    Column("dataset_version", String(160), nullable=False),
)


class EncryptedDatasetVault:
    """Persistent encrypted DatasetVault interface; single owner per service."""

    def __init__(self, engine: Engine, encryption_key: bytes):
        if engine.url.get_backend_name() not in ("postgresql", "sqlite"):
            raise ValueError("only PostgreSQL (or test SQLite) is supported")
        self.engine = engine
        self._cipher = Fernet(encryption_key)

    def bootstrap_schema(self) -> None:
        """Development/test only; production schema changes require migrations."""
        _METADATA.create_all(self.engine)

    @staticmethod
    def _check(principal: Principal, tenant_id: str) -> None:
        if principal.role != "evaluation" or principal.tenant_id != tenant_id:
            raise AccessDenied("tenant-scoped independent evaluator required")

    @staticmethod
    def _fingerprint(case: Case) -> str:
        material = case.input_ref or digest({
            "artifact": case.expected_artifact,
            "tools": case.required_tool_calls,
            "effects": case.required_effect_proofs,
        })
        return sha256(material.encode("utf-8")).hexdigest()

    def register(self, principal: Principal, dataset: Dataset) -> None:
        self._check(principal, dataset.tenant_id)
        fingerprints = [self._fingerprint(case) for case in dataset.cases]
        if len(set(fingerprints)) != len(fingerprints):
            raise InvalidEvidence("duplicate source material in dataset")
        body = json.dumps(asdict(dataset), sort_keys=True, separators=(",", ":")).encode()
        ciphertext = self._cipher.encrypt(body)
        try:
            with self.engine.begin() as conn:
                conn.execute(insert(_DATASETS).values(
                    tenant_id=dataset.tenant_id, version=dataset.version,
                    split=dataset.split, payload=ciphertext,
                    payload_sha256=sha256(body).hexdigest()))
                for fp in fingerprints:
                    conn.execute(insert(_FINGERPRINTS).values(
                        tenant_id=dataset.tenant_id, fingerprint=fp,
                        dataset_version=dataset.version))
        except IntegrityError as exc:
            raise InvalidEvidence("immutable dataset revision or reused test input") from exc

    def read(self, principal: Principal, version: str) -> Dataset:
        # Query uses tenant predicate; absence is deliberately indistinguishable
        # from a record that exists only in another tenant.
        with self.engine.connect() as conn:
            row = conn.execute(select(_DATASETS).where(
                _DATASETS.c.tenant_id == principal.tenant_id,
                _DATASETS.c.version == version)).mappings().first()
        if row is None:
            raise AccessDenied("dataset not accessible")
        if principal.role not in ("evaluation", "optimizer"):
            raise AccessDenied("dataset role denied")
        if row["split"] != "tune" and principal.role != "evaluation":
            raise AccessDenied("gold validation/holdout is evaluation-only")
        try:
            raw = self._cipher.decrypt(row["payload"])
            if sha256(raw).hexdigest() != row["payload_sha256"]:
                raise InvalidEvidence("dataset digest mismatch")
            data = json.loads(raw)
            cases = tuple(Case(
                case_id=c["case_id"],
                expected_artifact=c["expected_artifact"],
                required_tool_calls=tuple(c.get("required_tool_calls", [])),
                required_effect_proofs=tuple(c.get("required_effect_proofs", [])),
                max_steps=c.get("max_steps", 25),
                input_ref=c.get("input_ref", ""),
                required_graph_events=tuple(c.get("required_graph_events", [])),
                required_memory_keys=tuple(c.get("required_memory_keys", [])),
            ) for c in data["cases"])
        except (InvalidToken, ValueError, KeyError, TypeError) as exc:
            raise InvalidEvidence("encrypted dataset is unreadable or invalid") from exc
        if data["tenant_id"] != principal.tenant_id or data["version"] != version or data["split"] != row["split"]:
            raise InvalidEvidence("stored dataset metadata is inconsistent")
        return Dataset(data["tenant_id"], data["version"], data["split"], cases)
