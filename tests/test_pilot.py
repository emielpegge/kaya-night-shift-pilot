from __future__ import annotations

import unittest
from pathlib import Path

from night_shift_pilot.contracts import APPROVED_TASK, BoundaryError
from night_shift_pilot.controller import finalize, prepare, verify_environment
from night_shift_pilot.worker import run


def environment(**overrides):
    base = {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "example/public-pilot",
        "GITHUB_RUN_ID": "123",
        "APPROVED_TASK": APPROVED_TASK,
        "NIGHT_SHIFT_STOP": "false",
    }
    return base | overrides


class PilotSafetyTests(unittest.TestCase):
    def protected(self, repository, branch):
        self.assertEqual(repository, "example/public-pilot")
        self.assertEqual(branch, "main")
        return True

    def test_preapproved_manual_main_task_prepares(self):
        prepared = prepare(environment(), self.protected)
        self.assertEqual(prepared["status"], "READY_FOR_MOCK_WORKER")
        self.assertEqual(prepared["spec"]["task_id"], APPROVED_TASK)

    def test_environment_checks_manual_main_stop_task_and_protection(self):
        cases = [
            (environment(GITHUB_EVENT_NAME="schedule"), "MANUAL_DISPATCH_REQUIRED"),
            (environment(GITHUB_REF="refs/heads/feature/x"), "MAIN_REF_REQUIRED"),
            (environment(NIGHT_SHIFT_STOP="true"), "EMERGENCY_STOP"),
            (environment(APPROVED_TASK="other"), "TASK_NOT_PREAPPROVED"),
        ]
        for values, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(BoundaryError, code):
                    verify_environment(values, self.protected)
        with self.assertRaisesRegex(BoundaryError, "MAIN_NOT_PROTECTED"):
            verify_environment(environment(), lambda *_: (_ for _ in ()).throw(BoundaryError("MAIN_NOT_PROTECTED")))

    def test_stop_blocks_worker_and_finalizer(self):
        prepared = prepare(environment(), self.protected)
        with self.assertRaisesRegex(BoundaryError, "EMERGENCY_STOP"):
            run(prepared, "true")
        result = run(prepared, "false")
        with self.assertRaisesRegex(BoundaryError, "EMERGENCY_STOP"):
            finalize(prepared, result, environment(NIGHT_SHIFT_STOP="true"))

    def test_tampered_handoff_never_finalizes(self):
        prepared = prepare(environment(), self.protected)
        bad_result = run(prepared, "false") | {"spec_sha256": "0" * 64}
        with self.assertRaisesRegex(BoundaryError, "WORKER_RESULT_MISMATCH"):
            finalize(prepared, bad_result, environment())

    def test_successful_flow_is_mock_only_and_has_no_publication(self):
        prepared = prepare(environment(), self.protected)
        report = finalize(prepared, run(prepared, "false"), environment())
        self.assertEqual(report["status"], "MOCK_COMPLETED_NO_PUBLICATION")
        self.assertIn("no_git_write_or_pull_request", report["guarantees"])

    def test_workflow_uses_only_pinned_allowlisted_actions_and_read_permissions(self):
        text = Path(".github/workflows/night-shift-public-mock.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("pull_request_target", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("pull-requests:", text)
        self.assertNotIn("${{ secrets.", text)
        self.assertNotIn("gh ", text)
        self.assertNotIn("curl ", text)
        import re
        actions = re.findall(r"uses: ([^@\s]+)@([a-f0-9]{40})", text)
        self.assertTrue(actions)
        self.assertTrue(all(name in {
            "actions/checkout", "actions/setup-python", "actions/upload-artifact", "actions/download-artifact"
        } for name, _ in actions))


if __name__ == "__main__":
    unittest.main()
