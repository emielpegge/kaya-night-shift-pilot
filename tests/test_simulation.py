from __future__ import annotations

import unittest
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from night_shift_pilot.router import TaskSpec, synthetic_profiles
from night_shift_pilot.simulation import Scenario, benchmark, markdown_report, simulate, synthetic_scenarios, synthetic_workload


def backend_task(**overrides) -> TaskSpec:
    base = dict(task_id="synthetic-test", kind="backend", complexity=1, risk="low",
        required_capabilities=frozenset({"code", "tests"}), required_quality="high",
        max_synthetic_budget_usd=3, paid_call_approved=True)
    return TaskSpec(**(base | overrides))


class RouterSimulationTests(unittest.TestCase):
    def test_workload_has_exactly_100_stable_synthetic_tasks(self):
        first, second = synthetic_workload(), synthetic_workload()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 100)
        self.assertEqual({task.kind for task in first}, {"backend", "frontend", "debugging", "research", "documentation", "architecture", "review"})
        self.assertTrue(all(task.task_id.startswith("synthetic-20261014-") for task in first))

    def test_simulation_is_deterministic_and_does_not_mutate_scenario_profiles(self):
        scenario = synthetic_scenarios()[2]
        before = scenario.profiles
        first = simulate(scenario, "intelligent_router")
        second = simulate(scenario, "intelligent_router")
        self.assertEqual(first, second)
        self.assertEqual(scenario.profiles, before)

    def test_capacity_is_reserved_only_after_selection_with_fallback_then_no_execution(self):
        first = replace(synthetic_profiles()[0], engine_id="first", supported_kinds=frozenset({"backend"}),
            capabilities=frozenset({"code", "tests"}), latency_rank=1, capacity_remaining=1)
        second = replace(first, engine_id="second", latency_rank=2, capacity_remaining=1)
        scenario = Scenario("capacity", "synthetic", (first, second))
        result = simulate(scenario, "intelligent_router", (backend_task(task_id="one"), backend_task(task_id="two"), backend_task(task_id="three")))
        self.assertEqual((result.selected, result.no_execution), (2, 1))
        self.assertEqual(result.tasks_per_engine, {"first": 1, "second": 1})
        self.assertEqual(result.fallbacks, 1)
        self.assertGreaterEqual(result.capacity_exhaustion_events, 1)
        self.assertEqual(scenario.profiles[0].capacity_remaining, 1)

    def test_budget_and_paid_approval_rejections_consume_nothing(self):
        paid = replace(synthetic_profiles()[0], engine_id="paid", billing_kind="synthetic_paid_mock",
            synthetic_cost_usd=2, capacity_remaining=3)
        scenario = Scenario("paid", "synthetic", (paid,))
        budget = simulate(scenario, "intelligent_router", (backend_task(max_synthetic_budget_usd=1),))
        approval = simulate(scenario, "intelligent_router", (backend_task(max_synthetic_budget_usd=2, paid_call_approved=False),))
        self.assertEqual((budget.selected, budget.total_synthetic_cost_usd), (0, 0))
        self.assertEqual((approval.selected, approval.total_synthetic_cost_usd), (0, 0))
        self.assertEqual((budget.budget_or_approval_blocked_tasks, approval.budget_or_approval_blocked_tasks), (1, 1))

    def test_quality_and_risk_rejections_are_reported(self):
        limited = replace(synthetic_profiles()[0], engine_id="limited", max_risk="low", quality="baseline")
        scenario = Scenario("limited", "synthetic", (limited,))
        result = simulate(scenario, "intelligent_router", (backend_task(risk="high"),))
        self.assertEqual(result.no_execution, 1)
        self.assertGreaterEqual(result.candidate_quality_or_risk_rejections, 1)

    def test_benchmark_has_three_comparable_scenarios_and_machine_readable_metrics(self):
        report = benchmark()
        self.assertEqual(report["workload_size"], 100)
        self.assertEqual(len(report["scenarios"]), 3)
        for scenario in report["scenarios"]:
            self.assertEqual([result["strategy"] for result in scenario["results"]],
                ["intelligent_router", "fixed_codex_mock", "capability_first"])
            self.assertTrue(all(result["handled"] + result["no_execution"] == 100 for result in scenario["results"]))
        rendered = markdown_report(report)
        self.assertIn("Synthetic Intelligent Engine Router benchmark", rendered)
        self.assertIn("NO_EXECUTION", rendered)

    def test_cli_writes_local_machine_and_markdown_reports(self):
        script = Path("scripts/run_synthetic_router_simulation.py").resolve()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report"
            subprocess.run([sys.executable, str(script), "--output-dir", str(output)], check=True, capture_output=True, text=True)
            payload = json.loads((output / "report.json").read_text(encoding="utf-8"))
            rendered = (output / "report.md").read_text(encoding="utf-8")
        self.assertEqual(payload["workload_size"], 100)
        self.assertIn("Synthetic Intelligent Engine Router benchmark", rendered)


if __name__ == "__main__":
    unittest.main()
