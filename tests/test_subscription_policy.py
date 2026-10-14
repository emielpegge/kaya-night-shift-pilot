from __future__ import annotations

import unittest
from dataclasses import replace

from night_shift_pilot.subscription_policy import (
    SUBSCRIPTION_POLICY_VERSION, SubscriptionQuotaSnapshot, evaluate_subscription_capacity,
)


def snapshot(**overrides) -> SubscriptionQuotaSnapshot:
    base = SubscriptionQuotaSnapshot(
        "synthetic-codex", SUBSCRIPTION_POLICY_VERSION, "SUBSCRIPTION_ONLY", 100,
        "AVAILABLE", None, False, False, False, False, True,
    )
    return replace(base, **overrides)


class SubscriptionPolicyTests(unittest.TestCase):
    def test_available_requires_subscription_only_evidence_and_manual_authorization(self):
        decision = evaluate_subscription_capacity(snapshot(), 101)
        self.assertEqual((decision.state, decision.code), ("AVAILABLE", "SUBSCRIPTION_CAPACITY_CONFIRMED"))
        self.assertEqual(evaluate_subscription_capacity(snapshot(manual_start_authorized=False), 101).state,
                         "MANUAL_REVIEW_REQUIRED")

    def test_limit_states_never_start_or_auto_resume_work(self):
        five_hour = evaluate_subscription_capacity(snapshot(quota_state="LIMIT_REACHED_5H", reset_at_epoch=200), 101)
        weekly = evaluate_subscription_capacity(snapshot(quota_state="LIMIT_REACHED_WEEKLY", reset_at_epoch=200), 101)
        self.assertEqual((five_hour.state, five_hour.next_state), ("LIMIT_REACHED_5H", "WAITING_FOR_RESET"))
        self.assertEqual((weekly.state, weekly.next_state), ("LIMIT_REACHED_WEEKLY", "WAITING_FOR_RESET"))
        self.assertEqual(evaluate_subscription_capacity(snapshot(quota_state="LIMIT_REACHED_5H", reset_at_epoch=101), 101).state,
                         "MANUAL_REVIEW_REQUIRED")

    def test_unknown_paused_and_paid_paths_fail_closed(self):
        self.assertEqual(evaluate_subscription_capacity(snapshot(quota_state="QUOTA_UNKNOWN"), 101).state,
                         "QUOTA_UNKNOWN")
        self.assertEqual(evaluate_subscription_capacity(snapshot(), 101, paused=True).state, "PAUSED")
        for field in ("api_billing_enabled", "extra_credits_allowed", "paid_reset_allowed", "automatic_fallback_enabled"):
            with self.subTest(field=field):
                self.assertEqual(evaluate_subscription_capacity(snapshot(**{field: True}), 101).code,
                                 "SUBSCRIPTION_ONLY_POLICY_VIOLATION")

    def test_malformed_snapshot_or_clock_is_quota_unknown(self):
        self.assertEqual(evaluate_subscription_capacity(None, 101).state, "QUOTA_UNKNOWN")
        self.assertEqual(evaluate_subscription_capacity(snapshot(observed_at_epoch=True), 101).state, "QUOTA_UNKNOWN")
        self.assertEqual(evaluate_subscription_capacity(snapshot(), True).state, "QUOTA_UNKNOWN")

    def test_stale_or_future_quota_evidence_never_becomes_available(self):
        self.assertEqual(evaluate_subscription_capacity(snapshot(observed_at_epoch=100), 401).code,
                         "CAPACITY_EVIDENCE_STALE")
        self.assertEqual(evaluate_subscription_capacity(snapshot(observed_at_epoch=102), 101).code,
                         "CAPACITY_EVIDENCE_STALE")
        self.assertEqual(evaluate_subscription_capacity(snapshot(observed_at_epoch=100), 401,
                                                        maximum_evidence_age_seconds=True).state,
                         "QUOTA_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
