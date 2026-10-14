from __future__ import annotations

import unittest
from dataclasses import replace

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
        self.assertEqual(decision.rationale, "TASK_POLICY_INVALID:TASK_COMPLEXITY_INVALID")
        self.assertEqual(decision.candidates, ())

    def test_every_invalid_task_field_fails_closed_without_exception(self):
        invalid_tasks = (
            task(task_id=""), task(kind="invalid"), task(complexity=0), task(complexity=True),
            task(risk="invalid"), task(required_capabilities=frozenset({""})),
            task(required_capabilities={"code"}), task(required_quality="invalid"),
            task(max_synthetic_budget_usd=-1), task(max_synthetic_budget_usd="0"),
            task(paid_call_approved="false"),
        )
        for invalid in invalid_tasks:
            with self.subTest(invalid=invalid):
                decision = route(invalid, synthetic_profiles())
                self.assertEqual(decision.status, "NO_EXECUTION")
                self.assertTrue(decision.rationale.startswith("TASK_POLICY_INVALID:"), decision.rationale)
                self.assertEqual(decision.candidates, ())

    def test_invalid_profiles_are_audited_and_cannot_win_selection(self):
        good = synthetic_profiles()[0]
        invalid_profiles = (
            replace(good, engine_id="negative-cost", synthetic_cost_usd=-1),
            replace(good, engine_id="invalid-billing", billing_kind="invalid"),
            replace(good, engine_id="negative-capacity", capacity_remaining=-1),
            replace(good, engine_id="bad-complexity", max_complexity=0),
            replace(good, engine_id="bad-risk", max_risk="invalid"),
            replace(good, engine_id="bad-quality", quality="invalid"),
            replace(good, engine_id="bad-kind", supported_kinds=frozenset({"invalid"})),
            replace(good, engine_id="bad-provider", provider=""),
            replace(good, engine_id="bad-capabilities", capabilities=frozenset({""})),
            replace(good, engine_id="bad-latency", latency_rank=0),
            replace(good, engine_id="unknown-with-cost", billing_kind="unknown", synthetic_cost_usd=0),
        )
        decision = route(task(), (good, *invalid_profiles))
        self.assertEqual(decision.selected_engine_id, "codex-mock")
        reasons = {candidate.engine_id: candidate.reasons for candidate in decision.candidates}
        self.assertIn("SYNTHETIC_COST_INVALID", reasons["negative-cost"])
        self.assertIn("BILLING_KIND_INVALID", reasons["invalid-billing"])
        self.assertIn("CAPACITY_INVALID", reasons["negative-capacity"])
        self.assertIn("ENGINE_COMPLEXITY_INVALID", reasons["bad-complexity"])
        self.assertIn("ENGINE_RISK_INVALID", reasons["bad-risk"])
        self.assertIn("ENGINE_QUALITY_INVALID", reasons["bad-quality"])
        self.assertIn("SUPPORTED_TASK_KINDS_INVALID", reasons["bad-kind"])
        self.assertIn("PROVIDER_INVALID", reasons["bad-provider"])
        self.assertIn("ENGINE_CAPABILITIES_INVALID", reasons["bad-capabilities"])
        self.assertIn("LATENCY_RANK_INVALID", reasons["bad-latency"])
        self.assertIn("UNKNOWN_BILLING_COST_INVALID", reasons["unknown-with-cost"])

    def test_duplicate_engine_ids_block_selection_and_fallback(self):
        first = synthetic_profiles()[0]
        second = replace(first, latency_rank=1)
        decision = route(task(), (first, second))
        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.fallback_engine_ids, ())
        self.assertEqual(len(decision.candidates), 2)
        self.assertTrue(all("DUPLICATE_ENGINE_ID" in candidate.reasons for candidate in decision.candidates))

    def test_routing_and_audit_order_are_deterministic(self):
        profiles = synthetic_profiles()
        self.assertEqual(route(task(), profiles), route(task(), tuple(reversed(profiles))))

    def test_invalid_feedback_fails_closed_without_profile_evaluation(self):
        decision = route(task(), synthetic_profiles(), [FeedbackRecord("codex-mock", 0, 5)])
        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.rationale, "FEEDBACK_POLICY_INVALID:FEEDBACK_RECORD_INVALID")
        self.assertEqual(decision.candidates, ())


if __name__ == "__main__":
    unittest.main()
