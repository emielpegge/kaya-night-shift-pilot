from __future__ import annotations

import unittest

from night_shift_pilot.router import EngineProfile, FeedbackRecord, TaskSpec, route, synthetic_profiles


def task(**overrides) -> TaskSpec:
    base = dict(
        task_id="synthetic-task-1", kind="backend", complexity=2, risk="medium",
        required_capabilities=frozenset({"code", "tests"}), required_quality="high",
        max_synthetic_budget_usd=0, paid_call_approved=False,
    )
    return TaskSpec(**(base | overrides))


class IntelligentEngineRouterTests(unittest.TestCase):
    def test_backend_selects_lowest_cost_eligible_mock_and_records_fallbacks(self):
        decision = route(task(), synthetic_profiles())
        self.assertEqual(decision.status, "SELECTED")
        self.assertEqual(decision.selected_engine_id, "codex-mock")
        self.assertEqual(decision.fallback_engine_ids, ())
        selected = next(candidate for candidate in decision.candidates if candidate.engine_id == "codex-mock")
        self.assertEqual(selected.reasons, ("LOWEST_ELIGIBLE_SYNTHETIC_COST",))
        paid = next(candidate for candidate in decision.candidates if candidate.engine_id == "synthetic-paid-mock")
        self.assertIn("SYNTHETIC_BUDGET_EXCEEDED", paid.reasons)
        self.assertIn("PAID_CALL_NOT_APPROVED", paid.reasons)

    def test_paid_mock_needs_explicit_approval_and_budget(self):
        paid = synthetic_profiles()[-1:]
        denied = route(task(max_synthetic_budget_usd=1), paid)
        self.assertEqual(denied.status, "NO_EXECUTION")
        self.assertIn("PAID_CALL_NOT_APPROVED", denied.candidates[0].reasons)
        approved = route(task(max_synthetic_budget_usd=1, paid_call_approved=True), paid)
        self.assertEqual(approved.selected_engine_id, "synthetic-paid-mock")

    def test_unknown_cost_capacity_and_non_mock_profiles_fail_closed(self):
        profiles = (
            EngineProfile("unknown", "future", True, True, frozenset({"backend"}), frozenset({"code", "tests"}), 3, "high", "high", 1, "unknown", None, 1),
            EngineProfile("empty", "future", True, True, frozenset({"backend"}), frozenset({"code", "tests"}), 3, "high", "high", 1, "mock_no_charge", 0, 0),
            EngineProfile("live", "future", False, True, frozenset({"backend"}), frozenset({"code", "tests"}), 3, "high", "high", 1, "mock_no_charge", 0, 1),
        )
        decision = route(task(), profiles)
        self.assertEqual(decision.status, "NO_EXECUTION")
        reasons = {candidate.engine_id: candidate.reasons for candidate in decision.candidates}
        self.assertIn("COST_NOT_VERIFIABLE", reasons["unknown"])
        self.assertIn("CAPACITY_UNAVAILABLE", reasons["empty"])
        self.assertIn("NOT_MOCK_ONLY", reasons["live"])

    def test_feedback_can_block_but_never_relaxes_quality(self):
        profiles = synthetic_profiles()[:1]
        decision = route(task(), profiles, [FeedbackRecord("codex-mock", 1, 1)])
        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertIn("FEEDBACK_QUALITY_UNMET", decision.candidates[0].reasons)

    def test_task_classes_route_deterministically(self):
        frontend = route(task(kind="frontend", required_capabilities=frozenset({"writing", "reasoning"})), synthetic_profiles())
        documentation = route(task(kind="documentation", complexity=1, risk="low", required_capabilities=frozenset({"writing"}), required_quality="standard"), synthetic_profiles())
        self.assertEqual(frontend.selected_engine_id, "claude-mock")
        self.assertEqual(documentation.selected_engine_id, "claude-mock")
        self.assertEqual(documentation.fallback_engine_ids, ("future-provider-mock",))

    def test_all_declared_task_classes_have_a_synthetic_route(self):
        capabilities = {
            "backend": frozenset({"code", "tests"}),
            "frontend": frozenset({"writing", "reasoning"}),
            "debugging": frozenset({"code", "tests"}),
            "research": frozenset({"research"}),
            "documentation": frozenset({"writing"}),
            "architecture": frozenset({"reasoning"}),
            "review": frozenset({"review"}),
        }
        for kind, required in capabilities.items():
            with self.subTest(kind=kind):
                decision = route(task(kind=kind, complexity=1, risk="low", required_capabilities=required), synthetic_profiles())
                self.assertEqual(decision.status, "SELECTED")

    def test_invalid_task_returns_no_execution_without_candidates(self):
        decision = route(task(complexity=99), synthetic_profiles())
        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.rationale, "TASK_POLICY_INVALID")
        self.assertEqual(decision.candidates, ())


if __name__ == "__main__":
    unittest.main()
