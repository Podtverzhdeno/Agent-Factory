from dataclasses import replace
import pytest

from quality_engine.application import EvidenceEnvelope, EvaluationWorkflow
from quality_engine.attestation import AttestedEvidence, HmacEvidenceVerifier
from quality_engine.core import (
    Case, Dataset, DatasetVault, EvaluationRequest, InvalidEvidence,
    ObservedRun, Principal, ToolCall
)


class SignedCollector:
    def __init__(self, signer, forged=False):
        self.signer = signer
        self.forged = forged

    def collect(self, request, case):
        env = EvidenceEnvelope(
            request.tenant_id, request.agent_spec_digest, request.dataset_version_ref,
            case.case_id, "trace://signed",
            ObservedRun(case.case_id, {"ok": True},
                        (ToolCall("lookup", effect_proof="audit:one"),),
                        graph_events=("tool.call", "tool.result")),
        )
        attested = self.signer.sign(env, key_id="runtime-01")
        return replace(attested, signature_hex="a"*64) if self.forged else attested


def prepared(forged=False):
    verifier = HmacEvidenceVerifier({"runtime-01": b"a"*32})
    vault = DatasetVault()
    principal = Principal("a", "evaluation")
    vault.register(principal, Dataset("a", "gold-v1", "holdout",
                                     (Case("c1", {"ok": True}, ("lookup",), ("audit:one",)),)))
    job = EvaluationRequest("a", "agent-a-v1", "digest-a1", "gold-v1", "policy-v1", "idem-1", "eval-1")
    wf = EvaluationWorkflow(vault, SignedCollector(verifier, forged=forged),
                            verifier=verifier, require_attestation=True)
    return principal, wf, job


def test_valid_signed_runtime_proof_passes():
    principal, wf, job = prepared()
    wf.submit(principal, job)
    assert wf.process(principal, "eval-1").status == "PASSED"


def test_forged_runtime_proof_blocks():
    principal, wf, job = prepared(forged=True)
    wf.submit(principal, job)
    result = wf.process(principal, "eval-1")
    assert result.status == "BLOCKED"
    assert result.error_code == "INVALID_EXECUTION_EVIDENCE"


def test_production_attestation_cannot_be_disabled_by_missing_verifier():
    with pytest.raises(ValueError):
        EvaluationWorkflow(DatasetVault(), object(), require_attestation=True)


def test_signature_binds_owning_tenant():
    v = HmacEvidenceVerifier({"runtime-01": b"a"*32})
    env = EvidenceEnvelope("tenant-a", "digest", "ds", "case", "trace",
                           ObservedRun("case", {"ok": True}))
    attested = v.sign(env, key_id="runtime-01")
    with pytest.raises(InvalidEvidence):
        v.verify(replace(attested, envelope=replace(env, tenant_id="tenant-b")))
