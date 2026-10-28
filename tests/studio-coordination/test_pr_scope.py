import unittest
from scripts.studio_pr_scope_gate import validate_pr, parse_pr_claim, LeaseRejected

SHA="a"*40
BODY=f"Task: STU-T05\nStudio-Agent: A03\nClaim-Generation: 1\nBase-SHA: {SHA}\n"
MANIFEST={"agents":[{"id":"A03","write_allowlist":["apps/studio/src/features/task-intake/**"]},
                    {"id":"A04","write_allowlist":["apps/studio/src/features/agents/**"]}]}
TASK={"task_id":"STU-T05","current_owner":"A03","claim_generation":1,"base_sha":SHA,
      "current_branch":"frontend/a03-task","assigned_workstream":"A03","status":"IN_PROGRESS"}
GOOD=["apps/studio/src/features/task-intake/Wizard.tsx"]

def check(body=BODY,pr_ref="frontend/a03-task",files=GOOD,task=TASK,owners=MANIFEST):
    return validate_pr(pr_body=body,pr_head_ref=pr_ref,files=files,
                       current_task=task,owner_manifest=owners)

class ScopeTests(unittest.TestCase):
    def test_valid(self): self.assertIsNone(check())
    def test_missing_claim(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_MISSING_CLAIM_HEADERS"): check(body="task unknown")
    def test_generation_revoked(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_STALE_GENERATION"): check(task={**TASK,"claim_generation":2})
    def test_wrong_actor(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_NOT_CURRENT_OWNER"): check(task={**TASK,"current_owner":"A04"})
    def test_wrong_branch(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_BRANCH_MISMATCH"): check(pr_ref="frontend/a01-task")
    def test_unknown_status(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_TASK_NOT_ACTIVE"): check(task={**TASK,"status":"BACKLOG"})
    def test_outside_path(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_OUTSIDE_OWNED_PATHS"): check(files=["apps/studio/package.json"])
    def test_mixed_good_and_bad(self):
        with self.assertRaisesRegex(LeaseRejected,"PR_OUTSIDE_OWNED_PATHS"): check(files=GOOD+["apps/studio/src/features/agents/Summary.tsx"])
    def test_dynamic_takeover_path(self):
        t={**TASK,"current_owner":"A04","claim_generation":2,
           "current_branch":"frontend/a04-takeover","delegated_file_scope_from":"A03"}
        body=f"Task: STU-T05\nStudio-Agent: A04\nClaim-Generation: 2\nBase-SHA: {SHA}\n"
        self.assertIsNone(check(body=body,pr_ref="frontend/a04-takeover",task=t))
    def test_wrong_scope_after_takeover(self):
        t={**TASK,"current_owner":"A04","claim_generation":2,
           "current_branch":"frontend/a04-takeover","delegated_file_scope_from":"A03"}
        body=f"Task: STU-T05\nStudio-Agent: A04\nClaim-Generation: 2\nBase-SHA: {SHA}\n"
        with self.assertRaisesRegex(LeaseRejected,"PR_OUTSIDE_OWNED_PATHS"):
            check(body=body,pr_ref="frontend/a04-takeover",
                  files=["apps/studio/src/features/agents/Mission.tsx"],task=t)

if __name__=="__main__": unittest.main()
