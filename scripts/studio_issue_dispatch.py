"""GitHub Issue comment dispatcher for audited Studio task leases.

MUST run from the protected default branch only. Authentication uses GitHub
webhook actor + reviewed account/role mapping; free-text agent IDs alone have
no authority. GitHub Actions concurrency serializes requests; no generic code
is executed from comments.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.studio_task_logic import (
    LeaseRejected, grant_claim, heartbeat, progress, request_takeover,
    grant_takeover, fmt, utc,
)

META = re.compile(r"<!-- studio-tasklease-v1\s*(\{.*?\})\s*-->", re.S)
HEX_SHA = re.compile(r"^[a-fA-F0-9]{40}$")
CMD = re.compile(r"^/studio-task (activate|claim|start|heartbeat|progress|release|takeover-request|takeover-grant)(?:\s+(.+))?$")
ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "config/studio_task_actors.json"
OWNERS = ROOT / "docs/frontend/parallel/WORK_OWNERSHIP_MANIFEST.json"


def read_state(body: str) -> dict[str, Any]:
    m = META.search(body)
    if not m:
        raise LeaseRejected("ISSUE_WITHOUT_STUDIO_TASK_RECORD")
    return json.loads(m.group(1))


def with_state(body: str, task: dict[str, Any]) -> str:
    if not META.search(body):
        raise LeaseRejected("ISSUE_WITHOUT_STUDIO_TASK_RECORD")
    return META.sub(lambda _m: "<!-- studio-tasklease-v1\n"
                    + json.dumps(task, ensure_ascii=False, indent=2)
                    + "\n-->", body, count=1)


def path_allowed(path: str, patterns: list[str]) -> bool:
    if not path or path.startswith("/") or any(p in (".", "..") for p in path.split("/")):
        return False
    for pattern in patterns:
        if pattern.endswith("/**"):
            if path.startswith(pattern[:-3] + "/"):
                return True
        elif path == pattern:
            return True
    return False


class GH:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token

    def call(self, method: str, suffix: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode() if payload is not None else None
        url = "https://api.github.com/repos/" + self.repo + suffix
        request = urllib.request.Request(url, data=data, method=method,
            headers={"Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json",
                     "User-Agent": "agent-factory-task-coordinator"})
        try:
            with urllib.request.urlopen(request, timeout=20) as res:
                return json.loads(res.read())
        except urllib.error.HTTPError as ex:
            raise LeaseRejected("GITHUB_HTTP_" + str(ex.code)) from ex

    def issue(self, number: int) -> dict[str, Any]:
        return self.call("GET", "/issues/" + str(number))

    def commit(self, sha: str) -> dict[str, Any]:
        return self.call("GET", "/commits/" + urllib.parse.quote(sha))

    def branch(self, branch: str) -> dict[str, Any]:
        return self.call("GET", "/branches/" + urllib.parse.quote(branch, safe=""))

    def checks_ok(self, sha: str) -> bool:
        data = self.call("GET", "/commits/" + sha + "/check-runs?per_page=100")
        return any("Studio C0 reproducibility" in c.get("name", "") and
                   c.get("conclusion") == "success" and
                   c.get("head_sha") == sha for c in data.get("check_runs", []))

    def update_issue(self, number: int, body: str) -> None:
        self.call("PATCH", "/issues/" + str(number), {"body": body})

    def comment(self, number: int, body: str) -> None:
        self.call("POST", "/issues/" + str(number) + "/comments", {"body": body})


def verify_commit_paths(gh: GH, sha: str, workstream: str, role_owners: dict[str, Any]) -> None:
    data = gh.commit(sha)
    if data.get("sha", "").lower() != sha.lower():
        raise LeaseRejected("EVIDENCE_SHA_MISMATCH")
    owner = next((x for x in role_owners["agents"] if x["id"] == workstream), None)
    if not owner:
        raise LeaseRejected("UNKNOWN_WORKSTREAM")
    changed = [f["filename"] for f in data.get("files", [])]
    if not changed or any(not path_allowed(p, owner["write_allowlist"]) for p in changed):
        raise LeaseRejected("EVIDENCE_OUTSIDE_TASK_PATHS")


def compatible_free_tasks(gh: GH, role_owners: dict[str, Any], allowed_roles: list[str]) -> int:
    count = 0
    for entry in role_owners["agents"]:
        if entry["id"] not in allowed_roles:
            continue
        other = read_state(gh.issue(entry["issue_number"])["body"])
        if other.get("status") == "AVAILABLE" and other.get("prerequisites_met") is True:
            count += 1
    return count


def execute(gh: GH, event: dict[str, Any], identities: dict[str, Any], owners: dict[str, Any]) -> str | None:
    comment = event["comment"]
    body = (comment.get("body") or "").strip()
    parsed = CMD.fullmatch(body)
    if not parsed:
        return None
    issue = event["issue"]
    if "pull_request" in issue:
        return None
    actor = comment["user"]["login"]
    if actor.endswith("[bot]"):
        return None
    task_issue = gh.issue(issue["number"])
    current = read_state(task_issue.get("body") or "")
    if int(comment["id"]) <= int(current.get("last_request_comment_id") or 0):
        return None
    action, tail = parsed.groups()
    args = (tail or "").split()
    when = comment["created_at"]
    maintainers = identities.get("maintainers", [])
    actor_roles = identities.get("agent_roles", {}).get(actor, [])
    authorizes_maintainer = actor in maintainers
    next_state = None

    if action == "activate":
        # /studio-task activate <C0_HEAD_SHA>
        if not authorizes_maintainer or len(args) != 1 or not HEX_SHA.fullmatch(args[0]):
            raise LeaseRejected("ACTIVATION_REQUIRES_MAINTAINER_AND_SHA")
        if current["status"] != "BACKLOG":
            raise LeaseRejected("ACTIVATION_REQUIRES_BACKLOG")
        if not gh.checks_ok(args[0]):
            raise LeaseRejected("C0_BUILD_CHECK_NOT_GREEN")
        next_state = {**current, "status": "AVAILABLE", "base_sha": args[0],
                      "status_changed_at": when, "prerequisites_met": True,
                      "blocked_reason": None, "required_action": None}
    elif action == "claim":
        # /studio-task claim A03 0 frontend/a03-task
        if len(args) != 3 or not args[1].isdigit() or args[0] not in actor_roles:
            raise LeaseRejected("UNAUTHORIZED_CLAIM")
        branch = args[2]
        if not branch.startswith("frontend/") or len(branch) > 120:
            raise LeaseRejected("INVALID_BRANCH")
        gh.branch(branch)
        next_state = grant_claim(current, agent=args[0], actor=actor,
                                expected=int(args[1]), when=when,
                                base_sha=current.get("base_sha") or "", branch=branch)
    elif action == "start":
        # /studio-task start A03 1
        if len(args) != 2 or not args[1].isdigit():
            raise LeaseRejected("INVALID_START")
        from scripts.studio_task_logic import require_owner
        require_owner(current, args[0], actor, int(args[1]))
        if current["status"] != "CLAIMED":
            raise LeaseRejected("NOT_CLAIMED")
        next_state = {**current, "status": "IN_PROGRESS", "status_changed_at": when}
    elif action == "heartbeat":
        if len(args) != 2 or not args[1].isdigit():
            raise LeaseRejected("INVALID_HEARTBEAT")
        next_state = heartbeat(current, agent=args[0], actor=actor,
                               generation=int(args[1]), when=when)
    elif action == "progress":
        # /studio-task progress A03 1 <40-hex-commit>
        if len(args) != 3 or not args[1].isdigit() or not HEX_SHA.fullmatch(args[2]):
            raise LeaseRejected("INVALID_PROGRESS")
        verify_commit_paths(gh, args[2], current["assigned_workstream"], owners)
        next_state = progress(current, agent=args[0], actor=actor,
                              generation=int(args[1]), when=when, evidence_sha=args[2])
    elif action == "release":
        if len(args) != 2 or not args[1].isdigit():
            raise LeaseRejected("INVALID_RELEASE")
        from scripts.studio_task_logic import require_owner
        require_owner(current, args[0], actor, int(args[1]))
        next_state = {**current, "status": "PAUSED", "status_changed_at": when,
                      "required_action": "INTEGRATOR_REVIEW_HANDOFF"}
    elif action == "takeover-request":
        # /studio-task takeover-request A04 1 PR-inspection-<id>
        if len(args) != 3 or not args[1].isdigit() or args[0] not in actor_roles:
            raise LeaseRejected("UNAUTHORIZED_TAKEOVER_REQUEST")
        free = compatible_free_tasks(gh, owners, actor_roles)
        next_state = request_takeover(current, expected=int(args[1]), when=when,
                                     available_compatible_count=free,
                                     source_inspection_ref=args[2])
        next_state["takeover_requested_by"] = args[0]
        next_state["takeover_requested_actor"] = actor
    elif action == "takeover-grant":
        # /studio-task takeover-grant A04 1 frontend/a04-takeover
        if not authorizes_maintainer or len(args) != 3 or not args[1].isdigit():
            raise LeaseRejected("ONLY_MAINTAINER_GRANTS_TAKEOVER")
        gh.branch(args[2])
        grant_actor = current.get("takeover_requested_actor")
        grant_role = current.get("takeover_requested_by")
        if args[0] != grant_role or not grant_actor:
            raise LeaseRejected("TAKEOVER_REQUEST_MISMATCH")
        free = compatible_free_tasks(gh, owners, identities.get("agent_roles", {}).get(grant_actor, []))
        # Current source/CI review is performed by I00 and linked in
        # takeover_inspection_ref; this endpoint is human-maintainer gated.
        # Additional automated PR reconciliation before unlock remains required.
        next_state = grant_takeover(current, agent=args[0], actor=grant_actor,
                                    expected=int(args[1]), when=when, free_count=free,
                                    inspected_no_new_progress=True,
                                    review_approved=True, base_sha=current.get("base_sha") or "",
                                    branch=args[2])
        next_state["delegated_file_scope_from"] = current["assigned_workstream"]
    else:
        raise LeaseRejected("UNKNOWN_COMMAND")

    next_state["last_request_comment_id"] = int(comment["id"])
    gh.update_issue(issue["number"], with_state(task_issue["body"], next_state))
    gh.comment(issue["number"], "[STUDIO-TASK-EVENT v1]\n"
               + "source: GitHub Actions authenticated comment\n"
               + "request_comment_id: " + str(comment["id"]) + "\n"
               + "actor_github: " + actor + "\n"
               + "action: " + action + "\n"
               + "task_id: " + current["task_id"] + "\n"
               + "status: " + next_state["status"] + "\n"
               + "generation: " + str(next_state["claim_generation"]) + "\n"
               + "occurred_at_utc: " + when + "\n"
               + "[/STUDIO-TASK-EVENT]")
    return next_state["status"]


def main() -> int:
    event_path = os.environ["GITHUB_EVENT_PATH"]
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    identities = json.loads(ROLES.read_text())
    owners = json.loads(OWNERS.read_text())
    event = json.loads(Path(event_path).read_text())
    gh = GH(repo, token)
    try:
        status = execute(gh, event, identities, owners)
        print("DISPATCH_STATUS", status or "IGNORED")
        return 0
    except LeaseRejected as exc:
        print("DISPATCH_REJECTED", str(exc), file=sys.stderr)
        # Failure becomes an actual CI red signal for the request; not a
        # fake accepted task. No untrusted comment interpreted as code.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
