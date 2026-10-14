from __future__ import annotations

import unittest
from decimal import Decimal

from night_shift_pilot.codex_feasibility import TokenPrice, TokenScenario, estimate, validate_price, validate_scenario


PRICE = TokenPrice("gpt-5.3-codex", "1.75", "14.00", "2026-10-14")


class CodexFeasibilityTests(unittest.TestCase):
    def test_estimates_are_deterministic_and_keep_cost_components_separate(self):
        result = estimate(PRICE, TokenScenario("expected", 4000, 1000), 100)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.input_cost_usd, Decimal("0.700"))
        self.assertEqual(result.output_cost_usd, Decimal("1.400"))
        self.assertEqual(result.additional_cost_usd, Decimal("0"))
        self.assertEqual(result.total_cost_usd, Decimal("2.100"))
        self.assertEqual(result, estimate(PRICE, TokenScenario("expected", 4000, 1000), 100))

    def test_invalid_prices_scenarios_and_counts_fail_closed(self):
        self.assertFalse(validate_price(TokenPrice("", "1.75", "14", "2026-10-14")))
        self.assertFalse(validate_price(TokenPrice("model", "-1", "14", "2026-10-14")))
        self.assertFalse(validate_scenario(TokenScenario("low", -1, 1)))
        self.assertFalse(validate_scenario(TokenScenario("low", True, 1)))
        self.assertIsNone(estimate(PRICE, TokenScenario("low", 1, 1), -1))
        self.assertIsNone(estimate(PRICE, TokenScenario("low", 1, 1), True))
        self.assertIsNone(estimate(PRICE, TokenScenario("low", 1, 1), 1, "-0.01"))

    def test_task_count_scales_without_implying_provider_usage(self):
        scenario = TokenScenario("high", 12_000, 3_000)
        self.assertEqual(estimate(PRICE, scenario, 1).total_cost_usd, Decimal("0.06300"))
        self.assertEqual(estimate(PRICE, scenario, 1000).total_cost_usd, Decimal("63.00000"))


if __name__ == "__main__":
    unittest.main()
