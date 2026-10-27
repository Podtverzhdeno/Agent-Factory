"""Kafka delivery port on transactional outbox (at least once).

Broker acknowledgment precedes SQL acknowledgement. If a crash occurs between
them, consumers MUST de-duplicate by event_id.
"""
from __future__ import annotations

import json
from typing import Protocol

from .primitives import Principal
from .sql_jobs import SqlEvaluationJobStore


class EventTransport(Protocol):
    def publish(self, *, topic: str, key: bytes, value: bytes) -> None: ...


class OutboxPublisher:
    def __init__(self, store: SqlEvaluationJobStore, transport: EventTransport,
                 *, topic: str = "agent-factory.evaluations.v1"):
        if not topic or "*" in topic or "#" in topic:
            raise ValueError("explicit Kafka topic required")
        self._store, self._transport, self._topic = store, transport, topic

    def publish_batch(self, principal: Principal, *, batch_size: int = 100) -> int:
        published = 0
        for event in self._store.pending_events(principal, limit=batch_size):
            encoded = json.dumps(event.payload, sort_keys=True, allow_nan=False).encode()
            self._transport.publish(
                topic=self._topic, key=f"{event.tenant_id}:{event.run_id}".encode(),
                value=encoded,
            )
            if self._store.mark_dispatched(principal, event.event_id):
                published += 1
        return published


class KafkaPythonTransport:
    """Adapter for a configured kafka-python producer with synchronous ACK."""
    def __init__(self, producer, *, timeout_seconds: float = 15):
        if producer is None or timeout_seconds <= 0:
            raise ValueError("configured Kafka producer and timeout required")
        self._producer = producer
        self._timeout = timeout_seconds

    def publish(self, *, topic: str, key: bytes, value: bytes) -> None:
        self._producer.send(topic, key=key, value=value).get(timeout=self._timeout)
