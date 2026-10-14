from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from night_shift_pilot.local_execution import (
    LOCAL_EXECUTION_VERSION, LocalExecutionStore, LocalExecutionStoreError,
    StoredCheckpoint, dry_run_preflight, offline_demo_preflight,
)
from night_shift_pilot.local_workflow import (
    DEMO_TASK_ID, LocalWorkflowError, _preflight_request, main, recover_demo,
    PILOT_REPOSITORY_ROOT, run_demo, start_interrupted_demo, status_payload,
)


class LocalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.stop_environment = patch.dict(os.environ, {"NIGHT_SHIFT_STOP": "true"})
        self.stop_environment.start()

    def tearDown(self):
        self.stop_environment.stop()
        self.temporary.cleanup()

    def store(self):
        return LocalExecutionStore(self.root / "runtime", repository_root=self.root / "repository")

    def run_cli(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--store", str(self.root / "runtime"), *arguments])
        return exit_code, json.loads(output.getvalue())

    def test_complete_offline_demo_recovers_then_stores_result(self):
        report = run_demo(self.store())
        self.assertEqual(report["mode"], "OFFLINE_SYNTHETIC_DEMO_ONLY")
        self.assertEqual(report["task_status"], "COMPLETED")
        self.assertEqual(report["checkpoint_count"], 4)
        self.assertEqual(report["review"], "SIMULATED_APPROVAL_NOT_HUMAN_DECISION")
        state = status_payload(self.store())
        self.assertEqual(state["synthetic_result"]["synthetic_result"], "synthetic_local_workflow_completed")
        self.assertEqual(state["task"]["review_status"], "APPROVED")

    def test_interrupt_then_cli_recover_and_human_review(self):
        exit_code, interrupted = self.run_cli("demo", "--interrupt-only")
        self.assertEqual((exit_code, interrupted["task_status"]), (0, "PAUSED_INCOMPLETE"))
        exit_code, recovered = self.run_cli("recover")
        self.assertEqual((exit_code, recovered["task_status"]), (0, "COMPLETED"))
        exit_code, approved = self.run_cli("review", "APPROVED")
        self.assertEqual((exit_code, approved["review_status"]), (0, "APPROVED"))
        exit_code, rejected = self.run_cli("review", "REJECTED")
        self.assertEqual((exit_code, rejected["review_status"]), (0, "REJECTED"))
        exit_code, status = self.run_cli("status")
        self.assertEqual((exit_code, status["task"]["task_status"]), (0, "COMPLETED"))
        self.assertEqual(status_payload(self.store())["task"]["task_status"], "COMPLETED")

    def test_corrupt_storage_duplicate_attempt_and_uncertain_outcome_block(self):
        store = self.store()
        start_interrupted_demo(store)
        with self.assertRaisesRegex(LocalExecutionStoreError, "DUPLICATE_EXECUTION_ATTEMPT_ID"):
            store.save_checkpoint(StoredCheckpoint(
                LOCAL_EXECUTION_VERSION, DEMO_TASK_ID, "offline-demo-attempt-started",
                "PAUSED_INCOMPLETE", "APPROVED", "duplicate-checkpoint", False,
            ))
        task_path = store._task_path(DEMO_TASK_ID)
        task_path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(LocalExecutionStoreError, "STORE_CORRUPT"):
            LocalExecutionStore(self.root / "runtime", repository_root=self.root / "repository")

    def test_corrupt_checkpoint_blocks_restart(self):
        store = self.store()
        start_interrupted_demo(store)
        store._checkpoint_path("offline-demo-attempt-interrupted").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(LocalExecutionStoreError, "STORE_CORRUPT"):
            LocalExecutionStore(self.root / "runtime", repository_root=self.root / "repository")

    def test_missing_human_authorization_and_uncertain_outcome_block_recovery(self):
        store = self.store()
        paused, _ = start_interrupted_demo(store)
        store.record_review(DEMO_TASK_ID, "REJECTED")
        with self.assertRaisesRegex(LocalWorkflowError, "HUMAN_AUTHORIZATION_REQUIRED"):
            recover_demo(store)
        store.record_review(DEMO_TASK_ID, "APPROVED")
        store.save_checkpoint(StoredCheckpoint(
            LOCAL_EXECUTION_VERSION, DEMO_TASK_ID, "offline-demo-attempt-uncertain",
            "UNKNOWN_PROVIDER_OUTCOME", "APPROVED", "uncertain-checkpoint", True,
        ))
        with self.assertRaisesRegex(LocalWorkflowError, "SYNTHETIC_DEMO_RECOVERY_BLOCKED"):
            recover_demo(store)

    def test_active_stop_is_required_and_regular_preflight_stays_blocked(self):
        store = self.store()
        task, _ = start_interrupted_demo(store)
        self.assertEqual(task.task_status, "PAUSED_INCOMPLETE")
        request = _preflight_request(task)
        self.assertEqual(offline_demo_preflight(request).code, "OFFLINE_DEMO_ONLY")
        self.assertEqual(dry_run_preflight(request).code, "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")
        self.assertEqual(
            offline_demo_preflight(replace(request, emergency_stop="false")).code,
            "OFFLINE_DEMO_REQUIRES_ACTIVE_STOP",
        )

    def test_demo_requires_explicit_true_process_stop_without_creating_a_task(self):
        for value in ("false", "invalid", None):
            with self.subTest(value=value):
                if value is None:
                    environment = patch.dict(os.environ, {}, clear=True)
                else:
                    environment = patch.dict(os.environ, {"NIGHT_SHIFT_STOP": value})
                with environment:
                    exit_code, report = self.run_cli("demo")
                self.assertEqual((exit_code, report["code"]), (2, "OFFLINE_DEMO_PREFLIGHT_OFFLINE_DEMO_REQUIRES_ACTIVE_STOP"))
                self.assertFalse((self.root / "runtime" / "tasks" / f"{DEMO_TASK_ID}.json").exists())

    def test_cli_refuses_a_runtime_directory_inside_this_repository(self):
        exit_code, report = self.run_cli("--store", str(PILOT_REPOSITORY_ROOT / "night-shift-local-runtime"), "status")
        self.assertEqual((exit_code, report["code"]), (2, "STORE_ROOT_INSIDE_REPOSITORY"))


if __name__ == "__main__":
    unittest.main()
