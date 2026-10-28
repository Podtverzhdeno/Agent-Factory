"""Fail-closed integration rule for feature PR changed paths and live task lease.

Run only on a trusted protected BASE branch with read-only GitHub API token.
Required PR body headers: Task, Studio-Agent, Claim-Generation, Base-SHA.
This gate does NOT itself authenticate a coding session; task grant is separate.
"""
from __future__ import annotations

import json
import re
from typing import Any

from scripts.studio_issue_dispatch import read_state, path_allowed, LeaseRejected

CLAIM_PATTERN = re.compile(r"(?m)^Task:\s*(STU-T\d{2})\s*$")
AGENT_PATTERN = re.compile(r"(?m)^Studio-Agent:\s*(A\d{2})\s*$")
GEN_PATTERN = re.compile(r"(?m)^Claim-Generation:\s*(\d+)\s*$")
BASE_PATTERN = re.compile(r"(?m)^Base-SHA:\s*([0-9a-fA-F]{40})\s*$")


def parse_pr_claim(body: str) -> dict[str, Any]:
    m = [p.search(body) for p in (CLAIM_PATTERN, AGENT_PATTERN, GEN_PATTERN, BASE_PATTERN)]
    if any(x is None for x in m):
        raise LeaseRejected("PR_MISSING_CLAIM_HEADERS")
    task_id, agent, generation, base = (x.group(1) for x in m if x)
    return {"task_id": task_id, "agent": agent, "generation": int(generation), "base_sha": base}


def validate_pr(*, pr_body: str, pr_head_ref: str, files: list[str],
                current_task: dict[str, Any],
                owner_manifest: dict[str, Any]) -> None:
    claim = parse_pr_claim(pr_body)
    if claim["task_id"] != current_task.get("task_id"):
        raise LeaseRejected("PR_TASK_MISMATCH")
    if claim["agent"] != current_task.get("current_owner"):
        raise LeaseRejected("PR_NOT_CURRENT_OWNER")
    if claim["generation"] != current_task.get("claim_generation"):
        raise LeaseRejected("PR_STALE_GENERATION")
    if claim["base_sha"].lower() != (current_task.get("base_sha") or "").lower():
        raise LeaseRejected("PR_BASE_MISMATCH")
    if current_task.get("current_branch") != pr_head_ref:
        raise LeaseRejected("PR_BRANCH_MISMATCH")
    if current_task.get("status") not in {"CLAIMED", "IN_PROGRESS", "IN_REVIEW"}:
        raise LeaseRejected("PR_TASK_NOT_ACTIVE")
    # On approved takeover, new actor temporarily writes ONLY the original
    # target work packet paths, never their own unrelated module paths.
    workstream = current_task.get("delegated_file_scope_from") or current_task.get("assigned_workstream")
    packet = next((a for a in owner_manifest.get("agents", [])
                   if a.get("id") == workstream), None)
    if not packet:
        raise LeaseRejected("UNKNOWN_PACKET_SCOPE")
    if not files:
        raise LeaseRejected("PR_EMPTY_FILE_LIST")
    if len(files) >= 100:
        raise LeaseRejected("PR_FILE_PAGINATION_REVIEW_REQUIRED")
    if any(not path_allowed(p, packet["write_allowlist"]) for p in files):
        raise LeaseRejected("PR_OUTSIDE_OWNED_PATHS")


def main() -> int:
    import os
    from pathlib import Path
    from scripts.studio_issue_dispatch import GH
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pr = event["pull_request"]
    gh = GH(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"])
    manifest = json.loads(Path("docs/frontend/parallel/WORK_OWNERSHIP_MANIFEST.json").read_text())
    claim = parse_pr_claim(pr.get("body") or "")
    packet = next((x for x in manifest["agents"] if x["task_id"] == claim["task_id"]), None)
    if not packet:
        raise LeaseRejected("NO_TASK_ISSUE")
    issue = gh.issue(packet["issue_number"])
    state = read_state(issue["body"])
    # Up to 100 files in a single API page; deny on exact page capacity
    # instead of accepting an incomplete/possibly forged file list.
    res = gh.call("GET", "/pulls/" + str(pr["number"]) + "/files?per_page=100")
    if not isinstance(res, list):
        raise LeaseRejected("INVALID_PR_FILE_RESPONSE")
    changed = [f["filename"] for f in res]
    validate_pr(pr_body=pr.get("body") or "", pr_head_ref=pr["head"]["ref"],
                files=changed, current_task=state, owner_manifest=manifest)
    print("PR_SCOPE_GRANTED", claim["task_id"], claim["agent"], claim["generation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
