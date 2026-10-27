import pytest
from sqlalchemy import create_engine, select
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from quality_engine.core import Case, Dataset, Principal, InvalidEvidence
from quality_engine.sql_vault import SqlDatasetVault, metadata, cases
from quality_engine.gold_crypto import AesGcmGoldCipher


def test_sealed_dataset_not_plaintext_in_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata.create_all(engine)
    key = AESGCM.generate_key(bit_length=256)
    cipher = AesGcmGoldCipher(lambda tenant: key)
    owner = Principal("tenant-a", "evaluation")
    vault = SqlDatasetVault(engine, cipher=cipher, require_encryption=True)
    vault.register(owner, Dataset("tenant-a", "v1", "holdout",
                                  (Case("c1", {"secret": "cost-price-123"}),)))
    with engine.connect() as conn:
        stored = conn.execute(select(cases.c.payload)).scalar_one()
    assert stored.startswith(AesGcmGoldCipher.PREFIX)
    assert "cost-price-123" not in stored
    assert vault.read(owner, "v1").cases[0].expected_artifact == {"secret": "cost-price-123"}
    with pytest.raises(InvalidEvidence):
        SqlDatasetVault(engine, cipher=AesGcmGoldCipher(lambda tenant: b"0"*32),
                        require_encryption=True).read(owner, "v1")
    engine.dispose()


def test_aead_binds_record_tenant_and_case_id():
    key = AESGCM.generate_key(bit_length=256)
    cipher = AesGcmGoldCipher(lambda tenant: key)
    message = cipher.seal(tenant="a", version="v1", case_id="c1", plaintext="top-secret")
    for t, v, c in (("b", "v1", "c1"), ("a", "v2", "c1"), ("a", "v1", "c2")):
        with pytest.raises(InvalidEvidence):
            cipher.open(tenant=t, version=v, case_id=c, ciphertext=message)
    assert cipher.open(tenant="a", version="v1", case_id="c1", ciphertext=message) == "top-secret"


def test_production_encryption_configuration_mandatory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with pytest.raises(ValueError):
        SqlDatasetVault(engine)
    engine.dispose()
