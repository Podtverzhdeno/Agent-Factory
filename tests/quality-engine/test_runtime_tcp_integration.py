"""TCP integration: local signed Runtime simulator -> HTTP -> Ed25519 -> SQL Evaluation.

This is a real loopback socket, but deliberately NOT Agent 04's deployed Runtime.
"""
from contextlib import contextmanager
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine

from quality_engine.attestation import canonical_evidence
from quality_engine.core import Case, Dataset, DatasetVault, EvaluationRequest, ObservedRun, Principal
from quality_engine.application import EvidenceEnvelope
from quality_engine.durable_workflow import DurableEvaluationWorkflow
from quality_engine.ed25519_audit import Ed25519EvidenceVerifier, RuntimeAuditPublicKey
from quality_engine.runtime_http import RuntimeEvidenceHTTPCollector
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata


@contextmanager
def local_runtime(private):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlsplit(self.path).query)
            if self.headers.get("Authorization") != "Bearer local-test-token":
                self.send_error(403)
                return
            assert params.get("case_id") == ["case1"]
            assert "input_ref" not in params
            envelope = EvidenceEnvelope(
                "tenant-a", "spec-digest", "holdout-v1", "case1", "trace://local-runtime",
                ObservedRun("case1", {"correct": True}, graph_events=("final",)),
                "eval-1",
            )
            payload = json.dumps({
                "envelope": asdict(envelope), "key_id": "runtime-1",
                "signature_hex": private.sign(canonical_evidence(envelope)).hex(),
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_local_tcp_runtime_http_ed25519_sql_evaluation(tmp_path):
    private = Ed25519PrivateKey.generate()
    verifier = Ed25519EvidenceVerifier({
        "runtime-1": RuntimeAuditPublicKey("tenant-a", private.public_key())})
    vault = DatasetVault()
    owner = Principal("tenant-a", "evaluation")
    vault.register(owner, Dataset("tenant-a", "holdout-v1", "holdout",
                                  (Case("case1", {"correct": True},
                                        input_ref="artifact://public-case"),)))
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'runs.sqlite'}")
    metadata.create_all(engine)
    try:
        with local_runtime(private) as addr:
            client = RuntimeEvidenceHTTPCollector(base_url=addr, service_token="local-test-token")
            try:
                workflow = DurableEvaluationWorkflow(
                    vault, client, SqlEvaluationJobStore(engine),
                    verifier=verifier, worker_id="evaluator", clock=lambda: 100,
                )
                req = EvaluationRequest("tenant-a", "artifact://spec", "spec-digest",
                                        "holdout-v1", "policy", "idemp", "eval-1")
                assert workflow.submit(owner, req).status == "QUEUED"
                result = workflow.process(owner, "eval-1")
                assert result.status == "PASSED"
                assert result.result.independent_acceptance
                assert len(SqlEvaluationJobStore(engine).pending_events(owner)) == 1
            finally:
                client.close()
    finally:
        engine.dispose()
