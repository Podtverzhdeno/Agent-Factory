import unittest

from scripts.studio_issue_dispatch import (
    LeaseRejected, execute, path_allowed, read_state, with_state,
    verify_takeover_no_new_work,
)

SHA = "a" * 40
OTHER = "b" * 40

def state():
    return {
        "schema_version": "studio.tasklease.v1",
        "task_id": "STU-T05",
        "assigned_workstream": "A03",
        "status": "BACKLOG",
        "claim_generation": 0,
        "current_owner": None,
        "base_sha": None,
        "last_progress_at": None,
        "last_heartbeat_at": None,
    }

def comment(action, no=1, who="alice"):
    return {
        "issue": {"number": 10},
        "comment": {"id": no, "body": "/studio-task " + action,
                    "created_at": "2026-10-28T12:15:00Z",
                    "user": {"login": who}},
    }

class FakeGH:
    def __init__(self):
        self.body = with_state("Issue info\n<!-- studio-tasklease-v1\n{}\n-->",
                               state())
        self.audit = []
        self.sha = SHA
        self.prs = []
        self.check_runs = []
    def issue(self, number):
        assert number == 10
        return {"number": number, "body": self.body}
    def checks_ok(self, sha):
        return sha == SHA
    def branch(self, branch):
        return {"commit": {"sha": self.sha}}
    def compare(self, base, head):
        return {"status": "identical" if base == head else "ahead"}
    def update_issue(self, number, body):
        self.body = body
    def comment(self, number, body):
        self.audit.append(body)
    def commit(self, sha):
        return {"sha": sha,
                "files": [{"filename": "apps/studio/src/features/task-intake/ready.ts"}]}
    def pull_requests_for_branch(self, branch):
        return self.prs
    def call(self, method, suffix, payload=None):
        if "check-runs" in suffix:
            return {"check_runs": self.check_runs}
        raise AssertionError("Unexpected API call " + suffix)

IDS = {"maintainers": ["alice"],
       "agent_roles": {"alice": ["A03"], "mallory": []}}
OWNER = {"agents": [{"id":"A03","issue_number":10,
                   "write_allowlist":["apps/studio/src/features/task-intake/**"]}]}

class TaskDispatcherTests(unittest.TestCase):
    def test_issue_json_roundtrip(self):
        gh=FakeGH()
        self.assertEqual(read_state(gh.body)["task_id"],"STU-T05")
        self.assertEqual(gh.body.count("studio-tasklease-v1"),1)
    def test_activation_requires_trusted_maintainer_and_green_sha(self):
        gh=FakeGH()
        with self.assertRaisesRegex(LeaseRejected,"ACTIVATION_REQUIRES_MAINTAINER"):
            execute(gh,comment("activate "+SHA,who="mallory"),IDS,OWNER)
        with self.assertRaisesRegex(LeaseRejected,"C0_BUILD_CHECK_NOT_GREEN"):
            execute(gh,comment("activate "+OTHER),IDS,OWNER)
        self.assertEqual(execute(gh,comment("activate "+SHA),IDS,OWNER),"AVAILABLE")
        self.assertEqual(read_state(gh.body)["last_request_comment_id"],1)
    def test_unauthorized_claim_rejected(self):
        gh=FakeGH()
        execute(gh,comment("activate "+SHA),IDS,OWNER)
        with self.assertRaisesRegex(LeaseRejected,"UNAUTHORIZED_CLAIM"):
            execute(gh,comment("claim A03 0 frontend/a03-task",no=2,who="mallory"),IDS,OWNER)
    def test_claim_and_fencing_and_duplicate(self):
        gh=FakeGH()
        execute(gh,comment("activate "+SHA),IDS,OWNER)
        self.assertEqual(execute(gh,comment("claim A03 0 frontend/a03-task",no=2),IDS,OWNER),"CLAIMED")
        self.assertEqual(read_state(gh.body)["claim_generation"],1)
        with self.assertRaisesRegex(LeaseRejected,"STALE_GENERATION"):
            execute(gh,comment("claim A03 0 frontend/a03-task",no=3),IDS,OWNER)
        self.assertIsNone(execute(gh,comment("claim A03 0 frontend/a03-task",no=2),IDS,OWNER))
    def test_progress_commit_is_scoped(self):
        gh=FakeGH()
        execute(gh,comment("activate "+SHA),IDS,OWNER)
        execute(gh,comment("claim A03 0 frontend/a03-task",no=2),IDS,OWNER)
        execute(gh,comment("start A03 1",no=3),IDS,OWNER)
        self.assertEqual(execute(gh,comment("progress A03 1 "+OTHER,no=4),IDS,OWNER),"IN_PROGRESS")
        self.assertEqual(read_state(gh.body)["last_evidence_sha"],OTHER)
        self.assertEqual(len(gh.audit),4)
    def test_path_matching_is_literal_for_next_routes(self):
        self.assertTrue(path_allowed("apps/studio/app/[locale]/x/page.tsx",
                                     ["apps/studio/app/[locale]/x/**"]))
        self.assertFalse(path_allowed("apps/studio/app/en/x/page.tsx",
                                     ["apps/studio/app/[locale]/x/**"]))
        self.assertFalse(path_allowed("../services/secret",["services/**"]))
    def test_open_stalled_pr_may_be_reviewed_not_auto_assumed_done(self):
        gh=FakeGH()
        t={"current_branch":"frontend/a03-task","takeover_requested_at":
           "2026-10-28T12:01:00Z","last_evidence_sha":SHA,"base_sha":SHA}
        gh.prs=[{"number":25,"state":"open","merged_at":None,
                 "updated_at":"2026-10-28T11:59:00Z"}]
        verify_takeover_no_new_work(gh,t)
        gh.prs[0]["updated_at"]="2026-10-28T12:05:00Z"
        with self.assertRaisesRegex(LeaseRejected,"NEW_PR_ACTIVITY"):
            verify_takeover_no_new_work(gh,t)
    def test_unreported_branch_work_blocks_takeover(self):
        gh=FakeGH()
        t={"current_branch":"frontend/a03-task","takeover_requested_at":
           "2026-10-28T12:01:00Z","last_evidence_sha":OTHER,"base_sha":SHA}
        with self.assertRaisesRegex(LeaseRejected,"UNREPORTED_BRANCH_PROGRESS"):
            verify_takeover_no_new_work(gh,t)
    def test_inprogress_ci_blocks_takeover(self):
        gh=FakeGH()
        gh.check_runs=[{"status":"in_progress"}]
        t={"current_branch":"frontend/a03-task","takeover_requested_at":
           "2026-10-28T12:01:00Z","last_evidence_sha":SHA,"base_sha":SHA}
        with self.assertRaisesRegex(LeaseRejected,"CI_STILL_RUNNING"):
            verify_takeover_no_new_work(gh,t)

if __name__=="__main__":
    unittest.main()
