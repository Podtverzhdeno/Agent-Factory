import unittest
from datetime import datetime, timedelta, timezone
from scripts.studio_task_logic import (
  LeaseRejected, grant_claim, heartbeat, progress, stale, choose_next,
  request_takeover, grant_takeover
)

START = "2026-10-28T10:00:00Z"
AFTER = "2026-10-28T12:01:00Z"
SHA = "a"*40
def task():
    return {"task_id":"STU-T05","assigned_workstream":"A03",
            "status":"AVAILABLE","claim_generation":0,"current_owner":None,
            "prerequisites_met":True,"priority":3}

def claim():
    return grant_claim(task(),agent="A03",actor="alice",expected=0,when=START,
                       base_sha=SHA,branch="frontend/a03-task")

class TaskLeaseTests(unittest.TestCase):
    def test_grant_claim_and_owner(self):
        t=claim()
        self.assertEqual((t["status"],t["claim_generation"],t["current_owner"]),
                         ("CLAIMED",1,"A03"))
        self.assertEqual(t["claimed_at"],START)
        self.assertEqual(t["lease_expires_at"],"2026-10-28T10:30:00Z")

    def test_two_simultaneous_claims_lose_on_generation(self):
        t=claim()
        with self.assertRaisesRegex(LeaseRejected,"STALE_GENERATION"):
            grant_claim(t,agent="A03",actor="bob",expected=0,when=START,base_sha=SHA,branch="other")

    def test_wrong_packet_denied(self):
        with self.assertRaisesRegex(LeaseRejected,"WRONG_PACKET"):
            grant_claim(task(),agent="A04",actor="bob",expected=0,when=START,base_sha=SHA,branch="other")

    def test_heartbeat_not_progress(self):
        t=heartbeat(claim(),agent="A03",actor="alice",generation=1,when="2026-10-28T11:00:00Z")
        self.assertIsNone(t["last_progress_at"])
        self.assertTrue(stale(t,AFTER))

    def test_progress_requires_new_evidence(self):
        t=progress(claim(),agent="A03",actor="alice",generation=1,when="2026-10-28T11:00:00Z",evidence_sha=SHA)
        self.assertFalse(stale(t,AFTER))
        with self.assertRaisesRegex(LeaseRejected,"DUPLICATE_EVIDENCE"):
            progress(t,agent="A03",actor="alice",generation=1,when=AFTER,evidence_sha=SHA)

    def test_no_progress_exact_120_min_not_stale(self):
        self.assertFalse(stale(claim(),"2026-10-28T12:00:00Z"))
        self.assertTrue(stale(claim(),AFTER))

    def test_available_preferred(self):
        t=claim()
        free={"task_id":"STU-T09","assigned_workstream":"A03","status":"AVAILABLE",
              "priority":10,"prerequisites_met":True}
        state,target=choose_next([t,free],eligible_workstreams={"A03"},now=AFTER)
        self.assertEqual((state,target["task_id"]),("CLAIM_AVAILABLE","STU-T09"))

    def test_stale_only_after_available_exhausted(self):
        state,target=choose_next([claim()],eligible_workstreams={"A03"},now=AFTER)
        self.assertEqual((state,target["task_id"]),("REVIEW_STALE","STU-T05"))

    def test_stale_request_requires_no_free_and_inspection(self):
        with self.assertRaisesRegex(LeaseRejected,"FREE_TASK_FIRST"):
            request_takeover(claim(),expected=1,when=AFTER,available_compatible_count=1,source_inspection_ref="PR#5")
        with self.assertRaisesRegex(LeaseRejected,"MISSING_PR_CI_INSPECTION"):
            request_takeover(claim(),expected=1,when=AFTER,available_compatible_count=0,source_inspection_ref="")

    def test_takeover_grace_and_review(self):
        t=request_takeover(claim(),expected=1,when=AFTER,available_compatible_count=0,source_inspection_ref="PR#5 commit:deadbeef CI#12")
        with self.assertRaisesRegex(LeaseRejected,"GRACE_PERIOD"):
            grant_takeover(t,agent="A04",actor="bob",expected=1,when="2026-10-28T12:02:00Z",
                           free_count=0,inspected_no_new_progress=True,review_approved=True,base_sha=SHA,branch="takeover")
        with self.assertRaisesRegex(LeaseRejected,"PR_OR_CI_PROGRESS_EXISTS"):
            grant_takeover(t,agent="A04",actor="bob",expected=1,when="2026-10-28T12:12:00Z",
                           free_count=0,inspected_no_new_progress=False,review_approved=True,base_sha=SHA,branch="takeover")
        new=grant_takeover(t,agent="A04",actor="bob",expected=1,when="2026-10-28T12:12:00Z",
                           free_count=0,inspected_no_new_progress=True,review_approved=True,base_sha=SHA,branch="takeover")
        self.assertEqual((new["claim_generation"],new["previous_owner"],new["current_owner"]),(2,"A03","A04"))
        with self.assertRaisesRegex(LeaseRejected,"STALE_GENERATION"):
            heartbeat(new,agent="A03",actor="alice",generation=1,when="2026-10-28T12:20:00Z")

    def test_owner_actor_must_match(self):
        with self.assertRaisesRegex(LeaseRejected,"NOT_OWNER"):
            heartbeat(claim(),agent="A03",actor="mallory",generation=1,when=AFTER)

    def test_unavailable_no_claim(self):
        t=task()
        t["status"]="BACKLOG"
        with self.assertRaisesRegex(LeaseRejected,"NOT_AVAILABLE"):
            grant_claim(t,agent="A03",actor="alice",expected=0,when=START,base_sha=SHA,branch="a")

    def test_naive_utc_rejected(self):
        with self.assertRaisesRegex(LeaseRejected,"timestamp must include offset"):
            grant_claim(task(),agent="A03",actor="alice",expected=0,when="2026-10-28T10:00:00",base_sha=SHA,branch="a")

    def test_new_owner_requires_review(self):
        t=request_takeover(claim(),expected=1,when=AFTER,available_compatible_count=0,source_inspection_ref="PR/CI evidence")
        with self.assertRaisesRegex(LeaseRejected,"HUMAN_OR_COORDINATOR_REVIEW_REQUIRED"):
            grant_takeover(t,agent="A04",actor="bob",expected=1,when="2026-10-28T12:20:00Z",
                           free_count=0,inspected_no_new_progress=True,review_approved=False,base_sha=SHA,branch="takeover")

if __name__=="__main__":
    unittest.main()
