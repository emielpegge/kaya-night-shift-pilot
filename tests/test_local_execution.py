from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from night_shift_pilot.local_execution import (
    LOCAL_EXECUTION_VERSION, LocalExecutionStore, LocalExecutionStoreError,
    PreflightRequest, StoredCheckpoint, SyntheticTaskArtifact, dry_run_preflight,
)


SHA = "a" * 64


def artifact(**overrides) -> SyntheticTaskArtifact:
    base = SyntheticTaskArtifact(
        LOCAL_EXECUTION_VERSION, "synthetic-task-1", "synthetic-local-development-task-v1",
        SHA, "example/public-synthetic-pilot", "feature/synthetic-local-task",
    )
    return replace(base, **overrides)


def checkpoint(**overrides) -> StoredCheckpoint:
    base = StoredCheckpoint(
        LOCAL_EXECUTION_VERSION, "synthetic-task-1", "attempt-1", "PAUSED_INCOMPLETE",
        "APPROVED", "checkpoint-1", False,
    )
    return replace(base, **overrides)


class LocalExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = LocalExecutionStore(self.root / "runtime", repository_root=self.root / "repository")

    def tearDown(self):
        self.temporary.cleanup()

    def create_approved_task(self):
        return self.store.create_task(artifact(), review_status="APPROVED")

    def preflight_request(self, task, **overrides) -> PreflightRequest:
        base = PreflightRequest(
            task, "example/public-synthetic-pilot", "feature/synthetic-local-task",
            ("docs", "night_shift_pilot", "tests"), ("night_shift_pilot", "tests"),
            "false", True, "chatgpt_subscription", False, False, False, False,
            "workspace-write", False, False, False,
        )
        return replace(base, **overrides)

    def test_store_load_and_restart_recover_incomplete_checkpoint(self):
        task = self.create_approved_task()
        self.assertEqual(self.store.load_task(task.artifact.task_id), task)
        saved = self.store.save_checkpoint(checkpoint())
        restarted = LocalExecutionStore(self.root / "runtime", repository_root=self.root / "repository")
        recovered = restarted.recover_incomplete()
        self.assertEqual(recovered, ((saved, checkpoint()),))

    def test_store_rejects_repository_root_corruption_and_duplicate_task_id(self):
        with self.assertRaisesRegex(LocalExecutionStoreError, "STORE_ROOT_INSIDE_REPOSITORY"):
            LocalExecutionStore(self.root / "repository" / "runtime", repository_root=self.root / "repository")
        self.store.create_task(artifact())
        with self.assertRaisesRegex(LocalExecutionStoreError, "DUPLICATE_TASK_ID"):
            self.store.create_task(artifact(input_digest_sha256="b" * 64))
        self.store._task_path("synthetic-task-1").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(LocalExecutionStoreError, "STORE_CORRUPT"):
            self.store.load_task("synthetic-task-1")

    def test_checkpoint_attempt_is_immutable_and_uncertain_outcome_never_completes(self):
        self.create_approved_task()
        self.store.save_checkpoint(checkpoint())
        with self.assertRaisesRegex(LocalExecutionStoreError, "DUPLICATE_EXECUTION_ATTEMPT_ID"):
            self.store.save_checkpoint(checkpoint())
        with self.assertRaisesRegex(LocalExecutionStoreError, "CHECKPOINT_INVALID"):
            self.store.save_checkpoint(checkpoint(execution_attempt_id="attempt-2", task_status="COMPLETED",
                                                 provider_outcome_uncertain=True))
        uncertain = checkpoint(execution_attempt_id="attempt-3", task_status="UNKNOWN_PROVIDER_OUTCOME",
                               provider_outcome_uncertain=True)
        saved = self.store.save_checkpoint(uncertain)
        self.assertEqual(saved.task_status, "UNKNOWN_PROVIDER_OUTCOME")
        self.assertEqual(self.store.load_checkpoint("synthetic-task-1", "attempt-3"), uncertain)
        with self.assertRaisesRegex(LocalExecutionStoreError, "UNRESOLVED_PROVIDER_OUTCOME"):
            self.store.save_checkpoint(checkpoint(execution_attempt_id="attempt-4", task_status="COMPLETED"))

    def test_execution_attempt_id_is_unique_across_tasks(self):
        self.create_approved_task()
        self.store.save_checkpoint(checkpoint())
        second = artifact(task_id="synthetic-task-2", input_digest_sha256="b" * 64)
        self.store.create_task(second, review_status="APPROVED")
        duplicate = checkpoint(task_id="synthetic-task-2")
        with self.assertRaisesRegex(LocalExecutionStoreError, "DUPLICATE_EXECUTION_ATTEMPT_ID"):
            self.store.save_checkpoint(duplicate)

    def test_preflight_allows_only_synthetic_offline_scope(self):
        decision = dry_run_preflight(self.preflight_request(self.create_approved_task()))
        self.assertEqual((decision.status, decision.code), ("ALLOWED", "OFFLINE_PREFLIGHT_ONLY"))

    def test_preflight_blocks_stop_main_missing_authorization_and_api_key(self):
        task = self.create_approved_task()
        cases = (
            (self.preflight_request(task, emergency_stop="true"), "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE"),
            (self.preflight_request(task, feature_branch="main"), "FEATURE_BRANCH_REQUIRED"),
            (self.preflight_request(task, human_authorized=False), "HUMAN_AUTHORIZATION_REQUIRED"),
            (self.preflight_request(task, auth_mode="api_key", api_key_mode=True), "API_KEY_MODE_FORBIDDEN"),
        )
        for request, code in cases:
            with self.subTest(code=code):
                self.assertEqual(dry_run_preflight(request).code, code)

    def test_preflight_blocks_paid_automatic_unsafe_and_uncertain_paths(self):
        task = self.create_approved_task()
        cases = (
            (self.preflight_request(task, paid_fallback_enabled=True), "PAID_OR_AUTOMATIC_PATH_FORBIDDEN"),
            (self.preflight_request(task, extra_credits_allowed=True), "PAID_OR_AUTOMATIC_PATH_FORBIDDEN"),
            (self.preflight_request(task, paid_reset_allowed=True), "PAID_OR_AUTOMATIC_PATH_FORBIDDEN"),
            (self.preflight_request(task, automatic_merge=True), "PAID_OR_AUTOMATIC_PATH_FORBIDDEN"),
            (self.preflight_request(task, automatic_deployment=True), "PAID_OR_AUTOMATIC_PATH_FORBIDDEN"),
            (self.preflight_request(task, sandbox_mode="danger-full-access"), "SANDBOX_SCOPE_INVALID"),
            (self.preflight_request(task, requested_directories=("../outside",)), "DIRECTORY_SCOPE_INVALID"),
            (self.preflight_request(task, previous_provider_outcome_uncertain=True), "PREVIOUS_PROVIDER_OUTCOME_UNCERTAIN"),
        )
        for request, code in cases:
            with self.subTest(code=code):
                self.assertEqual(dry_run_preflight(request).code, code)


if __name__ == "__main__":
    unittest.main()
