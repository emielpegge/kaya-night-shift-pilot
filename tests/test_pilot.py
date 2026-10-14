from __future__ import annotations

import unittest
from pathlib import Path
import subprocess
import sys
import tempfile
from dataclasses import replace
from unittest.mock import patch

from night_shift_pilot.contracts import APPROVED_TASK, BoundaryError, digest
from night_shift_pilot.controller import finalize, prepare, verify_environment, verify_prepared
from night_shift_pilot.router import RoutingDecision, route, synthetic_profiles
from night_shift_pilot.router_adapter import routing_handoff, task_for_approved_spec
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
        self.assertEqual(prepared["router"]["task_id"], APPROVED_TASK)
        self.assertEqual(prepared["router"]["router_decision"]["status"], "SELECTED")
        self.assertTrue(prepared["router"]["router_decision"]["selected_engine_id"].endswith("-mock"))

    def test_router_handoff_is_deterministic_and_audits_fallbacks(self):
        prepared = prepare(environment(), self.protected)
        self.assertEqual(prepared["router"], routing_handoff(prepared["spec"]))
        decision = prepared["router"]["router_decision"]
        self.assertEqual(decision["selected_engine_id"], "claude-mock")
        self.assertEqual(decision["fallback_engine_ids"], ["future-provider-mock"])
        self.assertTrue(any(candidate["outcome"] == "SKIPPED" for candidate in decision["candidates"]))

    def test_environment_checks_manual_main_stop_task_and_protection(self):
        cases = [
            (environment(GITHUB_EVENT_NAME="schedule"), "MANUAL_DISPATCH_REQUIRED"),
            (environment(GITHUB_REF="refs/heads/feature/x"), "MAIN_REF_REQUIRED"),
            (environment(APPROVED_TASK="other"), "TASK_NOT_PREAPPROVED"),
        ]
        for values, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(BoundaryError, code):
                    verify_environment(values, self.protected)
        with self.assertRaisesRegex(BoundaryError, "MAIN_NOT_PROTECTED"):
            verify_environment(environment(), lambda *_: (_ for _ in ()).throw(BoundaryError("MAIN_NOT_PROTECTED")))

    def test_only_exact_false_allows_prepare_worker_and_finalize(self):
        prepared = prepare(environment(), self.protected)
        result = run(prepared, "false")
        self.assertEqual(finalize(prepared, result, environment())["status"], "MOCK_COMPLETED_NO_PUBLICATION")
        blocked_values = (None, "", " ", "true", "TRUE", "False", "0", "false ")
        blocked_environments = [environment(NIGHT_SHIFT_STOP=value) for value in blocked_values]
        missing = environment()
        missing.pop("NIGHT_SHIFT_STOP")
        blocked_environments.append(missing)
        for blocked_environment in blocked_environments:
            value = blocked_environment.get("NIGHT_SHIFT_STOP")
            label = "missing" if "NIGHT_SHIFT_STOP" not in blocked_environment else repr(value)
            with self.subTest(phase="prepare", value=label):
                with self.assertRaisesRegex(BoundaryError, "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE"):
                    prepare(blocked_environment, self.protected)
            with self.subTest(phase="worker", value=label):
                with self.assertRaisesRegex(BoundaryError, "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE"):
                    run(prepared, value)
            with self.subTest(phase="finalize", value=label):
                with self.assertRaisesRegex(BoundaryError, "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE"):
                    finalize(prepared, result, blocked_environment)

    def test_tampered_handoff_never_finalizes(self):
        prepared = prepare(environment(), self.protected)
        bad_result = run(prepared, "false") | {"spec_sha256": "0" * 64}
        with self.assertRaisesRegex(BoundaryError, "WORKER_RESULT_MISMATCH"):
            finalize(prepared, bad_result, environment())

    def test_tampered_router_decision_or_prepared_handoff_blocks(self):
        prepared = prepare(environment(), self.protected)
        changed_router = prepared | {"router": prepared["router"] | {
            "router_decision": prepared["router"]["router_decision"] | {"selected_engine_id": "codex-mock"},
        }}
        with self.assertRaisesRegex(BoundaryError, "ROUTER_DECISION_INTEGRITY_FAILED"):
            run(changed_router, "false")
        changed_prepared = prepared | {"report_sha256": "0" * 64}
        with self.assertRaisesRegex(BoundaryError, "PREPARED_HANDOFF_INTEGRITY_FAILED"):
            verify_prepared(changed_prepared)
        with self.assertRaisesRegex(BoundaryError, "PREPARED_HANDOFF_CONTRACT_INVALID"):
            verify_prepared(prepared | {"phase": "FINALIZED"})
        self_consistent_router = changed_router["router"] | {
            "router_decision_sha256": digest(changed_router["router"]["router_decision"]),
        }
        self_consistent_prepared = prepared | {"router": self_consistent_router}
        self_consistent_prepared["report_sha256"] = digest({
            "phase": "PREPARED", "spec_sha256": prepared["spec_sha256"],
            "router_decision_sha256": self_consistent_router["router_decision_sha256"],
        })
        with self.assertRaisesRegex(BoundaryError, "ROUTER_DECISION_MISMATCH"):
            verify_prepared(self_consistent_prepared)

    def test_tampered_worker_result_or_task_id_blocks(self):
        prepared = prepare(environment(), self.protected)
        result = run(prepared, "false")
        with self.assertRaisesRegex(BoundaryError, "WORKER_RESULT_INTEGRITY_FAILED"):
            finalize(prepared, result | {"synthetic_result": "changed"}, environment())
        self_consistent_result = result | {"synthetic_result": "changed"}
        self_consistent_result["result_sha256"] = digest(
            {key: value for key, value in self_consistent_result.items() if key != "result_sha256"})
        with self.assertRaisesRegex(BoundaryError, "WORKER_RESULT_INVALID"):
            finalize(prepared, self_consistent_result, environment())
        wrong_task = result | {"task_id": "other"}
        wrong_task["result_sha256"] = digest({key: value for key, value in wrong_task.items() if key != "result_sha256"})
        with self.assertRaisesRegex(BoundaryError, "WORKER_ROUTER_RESULT_MISMATCH"):
            finalize(prepared, wrong_task, environment())

    def test_missing_selected_engine_and_router_no_execution_block(self):
        prepared = prepare(environment(), self.protected)
        missing_engine = prepared | {"router": prepared["router"] | {
            "router_decision": prepared["router"]["router_decision"] | {"selected_engine_id": None},
        }}
        with self.assertRaisesRegex(BoundaryError, "ROUTER_DECISION_INTEGRITY_FAILED"):
            run(missing_engine, "false")
        unsupported = tuple(replace(profile, supported_kinds=frozenset({"backend"})) for profile in synthetic_profiles())
        with patch("night_shift_pilot.router_adapter.synthetic_profiles", return_value=unsupported):
            with self.assertRaisesRegex(BoundaryError, "ROUTER_NO_EXECUTION"):
                prepare(environment(), self.protected)

    def test_non_mock_or_unknown_router_engine_blocks(self):
        prepared = prepare(environment(), self.protected)
        valid_decision = route(task_for_approved_spec(prepared["spec"]), synthetic_profiles())
        non_mock = tuple(replace(profile, mock_only=False) if profile.engine_id == "claude-mock" else profile
            for profile in synthetic_profiles())
        with patch("night_shift_pilot.router_adapter.synthetic_profiles", return_value=non_mock), \
                patch("night_shift_pilot.router_adapter.route", return_value=valid_decision):
            with self.assertRaisesRegex(BoundaryError, "ROUTER_ENGINE_NOT_MOCK_ONLY"):
                routing_handoff(prepared["spec"])
        unknown = replace(valid_decision, selected_engine_id="unknown-mock")
        with patch("night_shift_pilot.router_adapter.route", return_value=unknown):
            with self.assertRaisesRegex(BoundaryError, "ROUTER_ENGINE_UNKNOWN"):
                routing_handoff(prepared["spec"])

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

    def test_public_safety_audit_detects_canary_in_deleted_intermediate_commit(self):
        audit = Path("scripts/public_safety_audit.py").resolve()
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            def git(*args):
                return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
            git("init", "--initial-branch=main")
            git("config", "user.name", "Synthetic Tester")
            git("config", "user.email", "synthetic@users.noreply.github.com")
            (repo / "docs").mkdir()
            (repo / "docs" / "safe.md").write_text("safe synthetic baseline\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "Synthetic baseline")
            git("switch", "-c", "feature/transient-canary")
            canary = "-----BEGIN " + "SYNTHETIC PRIVATE KEY-----"
            transient = repo / "docs" / "transient.md"
            transient.write_text(canary + "\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "Add synthetic canary")
            transient.unlink()
            git("add", ".")
            git("commit", "-m", "Remove synthetic canary")
            result = subprocess.run(
                [sys.executable, str(audit), "--repository", str(repo), "--base-ref", "main"],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("denied public-content pattern in feature-branch commit", result.stdout)


if __name__ == "__main__":
    unittest.main()
