"""Fenced evaluation worker lease renewal for long-running model jobs.

A heartbeat only prevents duplicate worker claims; external side effects also
require their own durable idempotency and reconciliation.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Thread
from time import time
from typing import Callable

from .primitives import InvalidEvidence, Principal
from .sql_jobs import Claim, SqlEvaluationJobStore


@dataclass
class LeaseKeeper:
    store: SqlEvaluationJobStore
    principal: Principal
    claim: Claim
    lease_seconds: float
    clock: Callable[[], float] = time

    def __post_init__(self) -> None:
        if not 0 < self.lease_seconds <= 3600:
            raise ValueError("lease duration outside safe range")
        self._stop = Event()
        self._failed = Event()
        self._worker: Thread | None = None

    @property
    def lost(self) -> bool:
        return self._failed.is_set()

    def _heartbeat(self) -> None:
        interval = max(0.01, self.lease_seconds / 3)
        while not self._stop.wait(interval):
            try:
                self.store.renew_lease(
                    self.principal, self.claim,
                    now=self.clock(), lease_seconds=self.lease_seconds,
                )
            except Exception:
                self._failed.set()
                return

    def __enter__(self) -> "LeaseKeeper":
        if self._worker is not None:
            raise RuntimeError("lease keeper must not be restarted")
        self._worker = Thread(target=self._heartbeat, name="evaluation-lease-keeper", daemon=True)
        self._worker.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._worker is not None:
            self._worker.join(timeout=5)
        if self._failed.is_set() and exc is None:
            raise InvalidEvidence("evaluation lease lost; worker cannot publish result")
