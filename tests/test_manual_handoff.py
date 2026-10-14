from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from night_shift_pilot.local_workflow import main
from night_shift_pilot.manual_handoff import (
    ALLOWED_REPOSITORY, MANUAL_HANDOFF_VERSION, ManualHandoffError,
    ManualHandoffStore, ManualResult, ManualTaskArtifact, _result_digest,
)


TASK_ID = "manual-task-v0.12"
BRANCH = "feature/manual-task-v0.12"
SCOPE = "Update a synthetic local validation message."


def artifact(**overrides) -> ManualTaskArtifact:
    value = ManualTaskArtifact(MANUAL_HANDOFF_VERSION, TASK_ID, ALLOWED_REPOSITORY, BRANCH, SCOPE)
    return value.__class__(**{**value.__dict__, **overrides})


def result(task, *, outcome="COMPLETED") -> ManualResult:
    base = ManualResult(
        MANUAL_HANDOFF_VERSION, task.artifact.task_id, task.task_digest_sha256,
        outcome, "Synthetic supervised result summary.", "unittest: PASS", "",
    )
    return base.__class__(**{**base.__dict__, "report_digest_sha256": _result_digest(base)})


class ManualHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def store(self):
        return ManualHandoffStore(self.root / "runtime", repository_root=self.root / "repository")

    def run_cli(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--store", str(self.root / "runtime"), "task", *arguments])
        return exit_code, json.loads(output.getvalue())

    def test_cli_create_handoff_report_and_review(self):
        exit_code, created = self.run_cli("create", "--task-id", TASK_ID, "--branch", BRANCH, "--scope", SCOPE)
        self.assertEqual((exit_code, created["task"]["task_status"]), (0, "CREATED"))
        exit_code, shown = self.run_cli("show", TASK_ID)
        self.assertEqual((exit_code, shown["task"]["artifact"]["feature_branch"]), (0, BRANCH))
        exit_code, handoff = self.run_cli("handoff", TASK_ID)
        self.assertEqual((exit_code, handoff["mode"]), (0, "MANUAL_COPY_ONLY"))
        self.assertIn("Manual supervised Codex task", handoff["codex_prompt"])
        self.assertIn("Do not modify main", handoff["codex_prompt"])
        exit_code, reported = self.run_cli("report", TASK_ID, "--summary", "Synthetic result.", "--tests", "unittest: PASS")
        self.assertEqual((exit_code, reported["task"]["task_status"]), (0, "RESULT_REPORTED"))
        exit_code, approved = self.run_cli("review", TASK_ID, "APPROVED")
        self.assertEqual((exit_code, approved["task"]["review_status"]), (0, "APPROVED"))
        self.assertEqual(approved["task"]["task_status"], "RESULT_REPORTED")
        exit_code, rejected = self.run_cli("review", TASK_ID, "REJECTED")
        self.assertEqual((exit_code, rejected["task"]["review_status"]), (0, "REJECTED"))

    def test_restart_finds_incomplete_handoff_and_immutable_result_reloads(self):
        store = self.store()
        task = store.create_task(artifact())
        store.handoff(TASK_ID)
        restarted = self.store()
        self.assertEqual(restarted.incomplete_tasks(), (restarted.load_task(TASK_ID),))
        reported = restarted.report_result(result(restarted.load_task(TASK_ID)))
        loaded = self.store().load_result(TASK_ID)
        self.assertEqual(loaded.report_digest_sha256, result(restarted.load_task(TASK_ID)).report_digest_sha256)
        with self.assertRaisesRegex(ManualHandoffError, "MANUAL_RESULT_NOT_ELIGIBLE"):
            restarted.report_result(result(reported))

    def test_repository_branch_and_review_boundaries_fail_closed(self):
        store = self.store()
        with self.assertRaisesRegex(ManualHandoffError, "TASK_ARTIFACT_INVALID"):
            store.create_task(artifact(repository="example/other"))
        with self.assertRaisesRegex(ManualHandoffError, "TASK_ARTIFACT_INVALID"):
            store.create_task(artifact(feature_branch="main"))
        task = store.create_task(artifact())
        with self.assertRaisesRegex(ManualHandoffError, "REVIEW_REQUIRES_COMPLETED_RESULT"):
            store.review(TASK_ID, "APPROVED")
        store.handoff(TASK_ID)
        uncertain = store.report_result(result(store.load_task(TASK_ID), outcome="UNCERTAIN"))
        self.assertEqual(uncertain.task_status, "OUTCOME_UNCERTAIN")
        with self.assertRaisesRegex(ManualHandoffError, "REVIEW_REQUIRES_COMPLETED_RESULT"):
            store.review(TASK_ID, "REJECTED")

    def test_corrupt_result_and_duplicate_task_id_block(self):
        store = self.store()
        store.create_task(artifact())
        with self.assertRaisesRegex(ManualHandoffError, "DUPLICATE_TASK_ID"):
            store.create_task(artifact())
        store.handoff(TASK_ID)
        store.report_result(result(store.load_task(TASK_ID)))
        store._result_path(TASK_ID).write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ManualHandoffError, "STORE_CORRUPT"):
            self.store()


if __name__ == "__main__":
    unittest.main()
