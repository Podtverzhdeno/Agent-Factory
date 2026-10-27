import json
import pytest
from sqlalchemy import create_engine

from quality_engine.core import EvaluationRequest, Principal, EvaluationResult
from quality_engine.sql_jobs import SqlEvaluationJobStore, metadata
from quality_engine.outbox_publisher import OutboxPublisher, KafkaPythonTransport


class MemoryKafka:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []
    def publish(self, **kwargs):
        if self.fail:
            raise ConnectionError("broker unavailable")
        self.messages.append(kwargs)


def _scenario(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'outbox.db'}")
    metadata.create_all(engine)
    store = SqlEvaluationJobStore(engine)
    principal = Principal("a", "evaluation")
    req = EvaluationRequest("a", "spec-a", "digest-a", "gold", "policy", "idem", "run-1")
    store.submit(principal, req)
    claim = store.claim(principal, run_id="run-1", worker_id="worker", now=0)
    result = EvaluationResult("run-1", "digest-a", "gold", "PASSED", True, False,
                              1.0, 1, (), 0.2, 100, "digest:proof",
                              independent_acceptance=True, tenant_id="a")
    store.complete(principal, claim, now=1, status="PASSED", result=result)
    return store, principal


@pytest.fixture
def scenario(tmp_path):
    store, principal = _scenario(tmp_path)
    yield store, principal
    store.engine.dispose()


def test_transactional_outbox_publishes_only_scrubbed_event(scenario):
    store, principal = scenario
    kafka = MemoryKafka()
    pub = OutboxPublisher(store, kafka)
    assert pub.publish_batch(principal) == 1
    assert pub.publish_batch(principal) == 0
    assert len(kafka.messages) == 1
    sent = kafka.messages[0]
    assert sent["key"] == b"a:run-1"
    event = json.loads(sent["value"])
    assert event["event_id"] and event["correlation_id"] and event["occurred_at"]
    assert event["passed"] is True
    assert not any(x in str(event) for x in ("gold_answer", "prompt", "tool_input"))


def test_outbox_survives_failed_broker_and_retries(scenario):
    store, principal = scenario(tmp_path)
    with pytest.raises(ConnectionError):
        OutboxPublisher(store, MemoryKafka(fail=True)).publish_batch(principal)
    assert len(store.pending_events(principal)) == 1
    assert OutboxPublisher(store, MemoryKafka()).publish_batch(principal) == 1


def test_kafka_adapter_awaits_broker_ack():
    class Future:
        def get(self, timeout):
            assert timeout == 12
            return object()
    class Producer:
        def send(self, topic, **kwargs):
            assert topic == "events"
            assert kwargs["key"] == b"a"
            return Future()
    KafkaPythonTransport(Producer(), timeout_seconds=12).publish(
        topic="events", key=b"a", value=b"payload")
