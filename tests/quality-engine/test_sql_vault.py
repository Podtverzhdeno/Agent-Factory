import pytest
from sqlalchemy import create_engine

from quality_engine.core import Case, Dataset, InvalidEvidence, AccessDenied, Principal
from quality_engine.sql_vault import SqlDatasetVault, metadata


@pytest.fixture
def sql():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata.create_all(engine)
    yield SqlDatasetVault(engine, require_encryption=False)
    engine.dispose()


def test_persistent_gold_separation_and_roundtrip(sql):
    owner = Principal("company-a", "evaluation")
    gold = Dataset("company-a", "holdout-2026-01", "holdout",
                   (Case("rfq-01", {"quote": ["X"]},
                         required_tool_calls=("catalog.lookup",),
                         required_effect_proofs=("effect:123",),
                         input_ref="artifact://business/rfq-01"),))
    sql.register(owner, gold)
    restored = sql.read(owner, "holdout-2026-01")
    assert restored.cases[0] == gold.cases[0]
    assert sql.read(owner, gold.version) == restored
    for role in ("optimizer", "builder", "runtime"):
        with pytest.raises(AccessDenied):
            sql.read(Principal("company-a", role), gold.version)
    with pytest.raises(AccessDenied):
        sql.read(Principal("company-b", "evaluation"), gold.version)


def test_sql_version_and_gold_immutability(sql):
    owner = Principal("a", "evaluation")
    gold = Dataset("a", "tune-v1", "tune", (Case("a1", {"done": 1}),))
    sql.register(owner, gold)
    assert sql.read(Principal("a", "optimizer"), "tune-v1") == gold
    with pytest.raises(InvalidEvidence):
        sql.register(owner, gold)


def test_sql_rejects_cross_split_input_contamination(sql):
    owner = Principal("a", "evaluation")
    sql.register(owner, Dataset("a", "tune", "tune",
                                (Case("c1", {"ok": True}, input_ref="artifact://source-1"),)))
    with pytest.raises(InvalidEvidence):
        sql.register(owner, Dataset("a", "holdout", "holdout",
                                    (Case("c2", {"ok": False}, input_ref="artifact://source-1"),)))


def test_sql_register_cannot_cross_tenant(sql):
    with pytest.raises(AccessDenied):
        sql.register(Principal("a", "evaluation"),
                     Dataset("b", "v1", "holdout", (Case("c1", {"ok": True}),)))


def test_sql_vault_survives_new_repository_instance(tmp_path):
    path = tmp_path / "quality.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    metadata.create_all(engine)
    owner = Principal("tenant", "evaluation")
    SqlDatasetVault(engine, require_encryption=False).register(owner, Dataset(
        "tenant", "v1", "holdout", (Case("a", {"ok": True}),)))
    assert SqlDatasetVault(engine, require_encryption=False).read(owner, "v1").cases[0].expected_artifact == {"ok": True}
    engine.dispose()
