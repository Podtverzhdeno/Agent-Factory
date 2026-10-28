"""Pure, dependency-free state transitions for Studio task leases.

This module never calls GitHub. The trusted coordinator must authenticate actor,
serialize updates, inspect Issue/PR/CI evidence and apply these transitions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

ACTIVE = {"CLAIMED", "IN_PROGRESS"}
MIN_STALE = timedelta(hours=2)
HEARTBEAT_INTERVAL = timedelta(minutes=20)
LEASE_DURATION = timedelta(minutes=30)
PROPOSED_GRACE = timedelta(minutes=10)


class LeaseRejected(ValueError):
    pass


def utc(value: str) -> datetime:
    if not value:
        raise LeaseRejected("timestamp absent")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise LeaseRejected("invalid timestamp") from e
    if d.tzinfo is None:
        raise LeaseRejected("timestamp must include offset")
    return d.astimezone(timezone.utc)


def fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def require_generation(task: dict[str, Any], expected: int) -> None:
    if task.get("claim_generation") != expected:
        raise LeaseRejected("STALE_GENERATION")


def grant_claim(task: dict[str, Any], *, agent: str, actor: str, expected: int,
                when: str, base_sha: str, branch: str) -> dict[str, Any]:
    require_generation(task, expected)
    if task.get("status") != "AVAILABLE" or task.get("current_owner"):
        raise LeaseRejected("NOT_AVAILABLE")
    if task.get("assigned_workstream") != agent:
        raise LeaseRejected("WRONG_PACKET")
    if not actor or not branch or not base_sha:
        raise LeaseRejected("MISSING_CLAIM_IDENTITY_OR_BASE")
    t = utc(when)
    return {**task, "status": "CLAIMED", "current_owner": agent,
            "owner_github_actor": actor, "claim_generation": expected + 1,
            "claimed_at": fmt(t), "last_progress_at": None,
            "last_heartbeat_at": fmt(t), "status_changed_at": fmt(t),
            "lease_expires_at": fmt(t + LEASE_DURATION),
            "base_sha": base_sha, "current_branch": branch,
            "blocked_reason": None, "required_action": None}


def require_owner(task: dict[str, Any], agent: str, actor: str, generation: int) -> None:
    require_generation(task, generation)
    if task.get("current_owner") != agent or task.get("owner_github_actor") != actor:
        raise LeaseRejected("NOT_OWNER")
    if task.get("status") not in ACTIVE:
        raise LeaseRejected("NOT_ACTIVE")


def heartbeat(task: dict[str, Any], *, agent: str, actor: str, generation: int, when: str) -> dict[str, Any]:
    require_owner(task, agent, actor, generation)
    t = utc(when)
    prev = task.get("last_heartbeat_at")
    if prev is not None and t <= utc(prev):
        raise LeaseRejected("NON_MONOTONIC_HEARTBEAT")
    return {**task, "last_heartbeat_at": fmt(t),
            "lease_expires_at": fmt(t + LEASE_DURATION)}


def progress(task: dict[str, Any], *, agent: str, actor: str, generation: int,
             when: str, evidence_sha: str) -> dict[str, Any]:
    require_owner(task, agent, actor, generation)
    if len(evidence_sha) not in (40, 64) or any(c not in "0123456789abcdef" for c in evidence_sha.lower()):
        raise LeaseRejected("INVALID_EVIDENCE")
    if task.get("last_evidence_sha") == evidence_sha:
        raise LeaseRejected("DUPLICATE_EVIDENCE")
    t = utc(when)
    old = task.get("last_progress_at") or task.get("claimed_at")
    if old and t < utc(old):
        raise LeaseRejected("NON_MONOTONIC_PROGRESS")
    return {**task, "status": "IN_PROGRESS", "status_changed_at": fmt(t),
            "last_progress_at": fmt(t), "last_evidence_sha": evidence_sha,
            "last_heartbeat_at": fmt(t), "lease_expires_at": fmt(t + LEASE_DURATION)}


def stale(task: dict[str, Any], now: str) -> bool:
    if task.get("status") not in ACTIVE:
        return False
    anchor = task.get("last_progress_at") or task.get("claimed_at")
    if not anchor:
        return False
    return utc(now) - utc(anchor) > MIN_STALE


def choose_next(tasks: list[dict[str, Any]], *, eligible_workstreams: set[str], now: str) -> tuple[str, dict[str, Any] | None]:
    available = sorted(
        (x for x in tasks if x.get("status") == "AVAILABLE"
         and x.get("assigned_workstream") in eligible_workstreams
         and x.get("prerequisites_met") is True),
        key=lambda x: (-int(x.get("priority", 0)), x["task_id"]),
    )
    if available:
        return "CLAIM_AVAILABLE", available[0]
    candidates = sorted(
        (x for x in tasks if x.get("assigned_workstream") in eligible_workstreams and stale(x, now)),
        key=lambda x: (x.get("last_progress_at") or x.get("claimed_at"), x["task_id"]),
    )
    if candidates:
        return "REVIEW_STALE", candidates[0]
    return "NO_COMPATIBLE_WORK", None


def request_takeover(task: dict[str, Any], *, expected: int, when: str,
                     available_compatible_count: int,
                     source_inspection_ref: str) -> dict[str, Any]:
    require_generation(task, expected)
    if available_compatible_count != 0:
        raise LeaseRejected("FREE_TASK_FIRST")
    if not stale(task, when):
        raise LeaseRejected("NOT_STALE")
    if not source_inspection_ref.strip():
        raise LeaseRejected("MISSING_PR_CI_INSPECTION")
    return {**task, "status": "TAKEOVER_PENDING",
            "status_changed_at": fmt(utc(when)),
            "takeover_inspection_ref": source_inspection_ref,
            "takeover_requested_at": fmt(utc(when))}


def grant_takeover(task: dict[str, Any], *, agent: str, actor: str, expected: int,
                   when: str, free_count: int, inspected_no_new_progress: bool,
                   review_approved: bool, base_sha: str, branch: str) -> dict[str, Any]:
    require_generation(task, expected)
    if task.get("status") != "TAKEOVER_PENDING":
        raise LeaseRejected("TAKEOVER_NOT_PENDING")
    if free_count:
        raise LeaseRejected("FREE_TASK_FIRST")
    if not inspected_no_new_progress:
        raise LeaseRejected("PR_OR_CI_PROGRESS_EXISTS")
    if not review_approved:
        raise LeaseRejected("HUMAN_OR_COORDINATOR_REVIEW_REQUIRED")
    t = utc(when)
    requested = task.get("takeover_requested_at")
    if not requested or t - utc(requested) < PROPOSED_GRACE:
        raise LeaseRejected("GRACE_PERIOD")
    if not actor or not agent or not base_sha or not branch:
        raise LeaseRejected("MISSING_TAKEOVER_IDENTITY")
    return {**task, "previous_owner": task.get("current_owner"),
            "previous_owner_github_actor": task.get("owner_github_actor"),
            "current_owner": agent, "owner_github_actor": actor,
            "status": "CLAIMED", "claim_generation": expected + 1,
            "claimed_at": fmt(t), "last_heartbeat_at": fmt(t),
            "last_progress_at": None, "last_evidence_sha": None,
            "lease_expires_at": fmt(t + LEASE_DURATION),
            "status_changed_at": fmt(t), "base_sha": base_sha,
            "current_branch": branch,
            "takeover_granted_at": fmt(t)}
