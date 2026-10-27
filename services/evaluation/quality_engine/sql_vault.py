"""SQLAlchemy-backed gold dataset repository for component/SQL integration tests.

Engine and schema lifecycle are injected by composition root. No implicit DDL
at startup; production authentication and migrations remain infrastructure-owned.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy import (
    Column, ForeignKeyConstraint, Integer, MetaData, String, Table,
    Text, and_, select
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .datasets import Case, Dataset
from .primitives import AccessDenied, InvalidEvidence, Principal, digest
from .gold_crypto import AesGcmGoldCipher


metadata = MetaData()
datasets = Table(
    "evaluation_datasets", metadata,
    Column("tenant_id", String(200), primary_key=True),
    Column("version", String(200), primary_key=True),
    Column("split", String(32), nullable=False),
    Column("case_count", Integer, nullable=False),
)
cases = Table(
    "evaluation_cases", metadata,
    Column("tenant_id", String(200), primary_key=True),
    Column("version", String(200), primary_key=True),
    Column("case_id", String(200), primary_key=True),
    Column("payload", Text, nullable=False),
    ForeignKeyConstraint(["tenant_id", "version"],
                         ["evaluation_datasets.tenant_id", "evaluation_datasets.version"],
                         ondelete="CASCADE"),
)
fingerprints = Table(
    "evaluation_dataset_fingerprints", metadata,
    Column("tenant_id", String(200), primary_key=True),
    Column("fingerprint", String(128), primary_key=True),
    Column("split", String(32), nullable=False),
    Column("version", String(200), nullable=False),
)


def _signature(case: Case) -> str:
    return (
        "input:" + digest(case.input_ref)
        if case.input_ref else "gold:" + digest({
            "artifact": case.expected_artifact,
            "tool": case.required_tool_calls,
            "effects": case.required_effect_proofs,
        })
    )


class SqlDatasetVault:
    """SQL-bound data access; authorization still depends on trusted Principal.

    A caller-supplied role is NOT production IAM. The DB account must have no
    paths to customer data outside this service. For concurrent registration
    across split types, the unique fingerprints table prevents conflicting
    insertion but same-split reuse is intentionally disallowed.
    """

    def __init__(self, engine: Engine, *, cipher: AesGcmGoldCipher | None = None,
                 require_encryption: bool = True) -> None:
        if require_encryption and cipher is None:
            raise ValueError("encrypted gold storage requires tenant cipher")
        self._engine = engine
        self._cipher = cipher
        self._require_encryption = require_encryption

    def register(self, principal: Principal, dataset: Dataset) -> None:
        if principal.role != "evaluation" or principal.tenant_id != dataset.tenant_id:
            raise AccessDenied("tenant evaluation principal required")
        signatures = [_signature(c) for c in dataset.cases]
        if len(set(signatures)) != len(signatures):
            raise InvalidEvidence("duplicate source material in dataset")
        import json
        try:
            with self._engine.begin() as conn:
                conn.execute(datasets.insert().values(
                    tenant_id=dataset.tenant_id,
                    version=dataset.version, split=dataset.split,
                    case_count=len(dataset.cases),
                ))
                conn.execute(cases.insert(), [
                    dict(tenant_id=dataset.tenant_id, version=dataset.version,
                         case_id=case.case_id,
                         payload=self._encrypt(dataset.tenant_id, dataset.version, case.case_id,
                             json.dumps(asdict(case), sort_keys=True, allow_nan=False)))
                    for case in dataset.cases
                ])
                conn.execute(fingerprints.insert(), [
                    dict(tenant_id=dataset.tenant_id, fingerprint=sig,
                         split=dataset.split, version=dataset.version)
                    for sig in signatures
                ])
        except IntegrityError as exc:
            raise InvalidEvidence("version duplicate or dataset material reused") from exc


    def _encrypt(self, tenant: str, version: str, case_id: str, raw: str) -> str:
        if self._cipher is not None:
            return self._cipher.seal(tenant=tenant, version=version, case_id=case_id, plaintext=raw)
        if self._require_encryption:
            raise InvalidEvidence("encrypted gold required")
        return raw

    def _decrypt(self, tenant: str, version: str, case_id: str, raw: str) -> str:
        if raw.startswith(AesGcmGoldCipher.PREFIX):
            if self._cipher is None:
                raise InvalidEvidence("encrypted gold requires authorized tenant key")
            return self._cipher.open(tenant=tenant, version=version, case_id=case_id,
                                     ciphertext=raw)
        if self._require_encryption:
            raise InvalidEvidence("plaintext gold forbidden in encrypted repository")
        return raw

    def read(self, principal: Principal, version: str) -> Dataset:
        if principal.role not in ("evaluation", "optimizer"):
            raise AccessDenied("dataset is unavailable to this role")
        with self._engine.connect() as conn:
            row = conn.execute(select(datasets).where(and_(
                datasets.c.tenant_id == principal.tenant_id,
                datasets.c.version == version,
            ))).mappings().first()
            if row is None:
                raise AccessDenied("dataset unavailable")
            if row["split"] != "tune" and principal.role != "evaluation":
                raise AccessDenied("holdout/validation evaluator-only")
            records = conn.execute(select(cases.c.case_id, cases.c.payload).where(and_(
                cases.c.tenant_id == principal.tenant_id,
                cases.c.version == version,
            )).order_by(cases.c.case_id)).all()
        import json
        parsed: list[Case] = []
        tuple_fields = ("required_tool_calls", "required_effect_proofs",
                        "required_graph_events", "required_memory_keys")
        for case_id, record in records:
            fields: dict[str, Any] = json.loads(self._decrypt(principal.tenant_id, version, case_id, record))
            for name in tuple_fields:
                fields[name] = tuple(fields.get(name, ()))
            parsed.append(Case(**fields))
        if len(parsed) != row["case_count"]:
            raise InvalidEvidence("dataset storage consistency failure")
        return Dataset(principal.tenant_id, version, row["split"], tuple(parsed))
