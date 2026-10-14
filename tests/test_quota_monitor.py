from __future__ import annotations

import unittest
from dataclasses import replace

from night_shift_pilot.quota_monitor import (
    QUOTA_CONTRACT_VERSION, AppServerQuotaEvidence, BucketRequirement, ProviderQuotaContract,
    QuotaBucket, QuotaWindow, TaskCheckpoint, app_server_operation_allowed, assess_resume_candidate,
    backoff_recheck, checkpoint_for_quota, normalize_codex_quota, plan_recheck,
)


NOW = 10_000


def requirements(**overrides) -> ProviderQuotaContract:
    base = ProviderQuotaContract(QUOTA_CONTRACT_VERSION, "codex", "chatgpt", (
        BucketRequirement("codex_5h", "five_hour", False, frozenset({"five_hour"})),
        BucketRequirement("codex_week", "weekly", True, frozenset({"weekly"})),
    ))
    return replace(base, **overrides)


def window(percent=20, duration=60, reset=10_100):
    return QuotaWindow(percent, duration, reset)


def evidence(**overrides) -> AppServerQuotaEvidence:
    five = QuotaBucket("codex_5h", window(), None, None)
    weekly = QuotaBucket("codex_week", window(duration=10_080, reset=20_000), window(duration=60, reset=10_100), None)
    base = AppServerQuotaEvidence(QUOTA_CONTRACT_VERSION, "codex", "CHATGPT_SUBSCRIPTION", "chatgpt", "plus", NOW,
                                  True, (five, weekly), five, None)
    return replace(base, **overrides)


def checkpoint(**overrides) -> TaskCheckpoint:
    base = TaskCheckpoint("checkpoint-1", "synthetic-task", "a" * 64, "codex", "checkpoint-data",
                          "RUNNING", False, "AVAILABLE", None, (), "NOT_REVIEWED", False, "attempt-1")
    return replace(base, **overrides)


class QuotaMonitorTests(unittest.TestCase):
    def test_strict_read_only_allowlist_rejects_every_mutation(self):
        self.assertTrue(app_server_operation_allowed("account/read"))
        self.assertTrue(app_server_operation_allowed("account/rateLimits/read"))
        self.assertTrue(app_server_operation_allowed("account/rateLimits/updated", notification=True))
        for operation in ("account/rateLimitResetCredit/consume", "account/sendAddCreditsNudgeEmail",
                          "account/login/start", "account/usage/read", "agent/start"):
            with self.subTest(operation=operation):
                self.assertFalse(app_server_operation_allowed(operation))

    def test_valid_available_evidence_is_never_task_authorization(self):
        decision = normalize_codex_quota(evidence(), requirements(), NOW + 1)
        self.assertEqual((decision.state, decision.code), ("AVAILABLE", "CAPACITY_CONFIRMED"))
        self.assertTrue(decision.capacity_available)
        self.assertFalse(decision.task_start_authorized)

    def test_five_hour_weekly_and_both_limit_conditions_are_all_preserved(self):
        five = QuotaBucket("codex_5h", window(percent=100), None, None)
        weekly = QuotaBucket("codex_week", window(duration=10_080, reset=20_000), window(), None)
        result = normalize_codex_quota(evidence(rate_limits_by_limit_id=(five, weekly), legacy_rate_limits=five), requirements(), NOW + 1)
        self.assertEqual((result.state, result.blocking_limits), ("LIMIT_REACHED_5H", frozenset({"five_hour"})))
        weekly_reached = QuotaBucket("codex_week", window(duration=10_080, reset=20_000), window(percent=10), "weekly")
        result = normalize_codex_quota(evidence(rate_limits_by_limit_id=(QuotaBucket("codex_5h", window(), None, None), weekly_reached)), requirements(), NOW + 1)
        self.assertEqual((result.state, result.blocking_limits), ("LIMIT_REACHED_WEEKLY", frozenset({"weekly"})))
        both = normalize_codex_quota(evidence(rate_limits_by_limit_id=(five, weekly_reached), legacy_rate_limits=five), requirements(), NOW + 1)
        self.assertEqual((both.state, both.blocking_limits), ("LIMIT_REACHED_WEEKLY", frozenset({"five_hour", "weekly"})))

    def test_missing_unknown_or_invalid_buckets_fail_closed(self):
        self.assertEqual(normalize_codex_quota(evidence(rate_limits_by_limit_id=()), requirements(), NOW + 1).state, "QUOTA_UNKNOWN")
        unknown = QuotaBucket("other", window(), None, None)
        self.assertEqual(normalize_codex_quota(evidence(rate_limits_by_limit_id=(unknown,)), requirements(), NOW + 1).code,
                         "REQUIRED_OR_UNKNOWN_BUCKET_MISMATCH")
        missing_secondary = QuotaBucket("codex_week", window(duration=10_080, reset=20_000), None, None)
        self.assertEqual(normalize_codex_quota(evidence(rate_limits_by_limit_id=(QuotaBucket("codex_5h", window(), None, None), missing_secondary)), requirements(), NOW + 1).code,
                         "SECONDARY_WINDOW_REQUIRED")
        bad_percent = QuotaBucket("codex_5h", window(percent=101), None, None)
        self.assertEqual(normalize_codex_quota(evidence(rate_limits_by_limit_id=(bad_percent, evidence().rate_limits_by_limit_id[1]), legacy_rate_limits=bad_percent), requirements(), NOW + 1).code,
                         "PRIMARY_WINDOW_INVALID")

    def test_bad_timestamps_stale_future_untrusted_and_api_mode_block(self):
        bad_reset = QuotaBucket("codex_5h", window(reset=NOW - 1), None, None)
        self.assertEqual(normalize_codex_quota(evidence(rate_limits_by_limit_id=(bad_reset, evidence().rate_limits_by_limit_id[1])), requirements(), NOW + 1).state,
                         "QUOTA_UNKNOWN")
        self.assertEqual(normalize_codex_quota(evidence(observed_at_epoch=NOW - 301), requirements(), NOW).state, "QUOTA_UNKNOWN")
        self.assertEqual(normalize_codex_quota(evidence(observed_at_epoch=NOW + 1), requirements(), NOW).state, "QUOTA_UNKNOWN")
        self.assertEqual(normalize_codex_quota(evidence(source_attested=False), requirements(), NOW + 1).state, "QUOTA_UNKNOWN")
        self.assertEqual(normalize_codex_quota(evidence(auth_mode="apikey"), requirements(), NOW + 1).state, "QUOTA_UNKNOWN")

    def test_conflict_unknown_reached_type_and_reset_credit_require_review_or_block(self):
        inconsistent = QuotaBucket("codex_5h", window(), None, "weekly")
        self.assertEqual(normalize_codex_quota(evidence(rate_limits_by_limit_id=(inconsistent, evidence().rate_limits_by_limit_id[1]), legacy_rate_limits=inconsistent), requirements(), NOW + 1).code,
                         "REACHED_TYPE_UNKNOWN")
        other = QuotaBucket("codex_5h", window(percent=30), None, None)
        self.assertEqual(normalize_codex_quota(evidence(legacy_rate_limits=other), requirements(), NOW + 1).code,
                         "LEGACY_BUCKET_CONFLICT")
        self.assertEqual(normalize_codex_quota(evidence(reset_credit_count=1), requirements(), NOW + 1).state,
                         "MANUAL_REVIEW_REQUIRED")

    def test_recheck_is_idempotent_bounded_and_never_an_execution_plan(self):
        five = QuotaBucket("codex_5h", window(percent=100, reset=10_200), None, None)
        decision = normalize_codex_quota(evidence(rate_limits_by_limit_id=(five, evidence().rate_limits_by_limit_id[1]), legacy_rate_limits=five), requirements(), NOW + 1)
        plan = plan_recheck(decision, "checkpoint-1", NOW + 1)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual((plan.status, plan.scheduled_at_epoch), ("READ_ONLY_RECHECK_PLANNED", 10_205))
        self.assertIsNone(plan_recheck(decision, "checkpoint-1", NOW + 1, plan))
        retry = backoff_recheck(plan, 10_205)
        self.assertIsNotNone(retry)
        assert retry is not None
        self.assertEqual(retry.scheduled_at_epoch, 10_265)
        exhausted = replace(retry, attempt=5)
        self.assertIsNone(backoff_recheck(exhausted, 10_265))
        self.assertIsNone(plan_recheck(decision, "checkpoint-1", 10_300))

    def test_multiple_limits_recheck_one_then_remaining_limit_stays_blocked(self):
        five = QuotaBucket("codex_5h", window(percent=100, reset=10_100), None, None)
        weekly = QuotaBucket("codex_week", window(percent=100, duration=10_080, reset=20_000), window(reset=20_000), None)
        blocked = normalize_codex_quota(evidence(rate_limits_by_limit_id=(five, weekly), legacy_rate_limits=five), requirements(), NOW + 1)
        plan = plan_recheck(blocked, "checkpoint-1", NOW + 1)
        self.assertEqual(plan.scheduled_at_epoch, 10_105)
        recovered_five = QuotaBucket("codex_5h", window(reset=10_200), None, None)
        after_five = normalize_codex_quota(evidence(observed_at_epoch=10_105, rate_limits_by_limit_id=(recovered_five, weekly), legacy_rate_limits=recovered_five), requirements(), 10_106)
        self.assertEqual(after_five.state, "LIMIT_REACHED_WEEKLY")
        self.assertEqual(after_five.blocking_limits, frozenset({"weekly"}))

    def test_checkpoint_pauses_incomplete_work_and_capacity_is_not_resume_authorization(self):
        reached_five = QuotaBucket("codex_5h", window(percent=100), None, None)
        reached = normalize_codex_quota(evidence(rate_limits_by_limit_id=(reached_five, evidence().rate_limits_by_limit_id[1]), legacy_rate_limits=reached_five), requirements(), NOW + 1)
        paused = checkpoint_for_quota(checkpoint(), reached, NOW + 1)
        self.assertIsNotNone(paused)
        assert paused is not None
        self.assertEqual((paused.execution_status, paused.quota_state, paused.continuation_authorized),
                         ("PAUSED_INCOMPLETE", "LIMIT_REACHED_5H", False))
        available = normalize_codex_quota(evidence(observed_at_epoch=NOW + 2), requirements(), NOW + 3)
        candidate = assess_resume_candidate(paused, available, "false")
        self.assertEqual((candidate.status, candidate.task_start_authorized),
                         ("CANDIDATE_REQUIRES_NEW_AUTHORIZATION", False))
        self.assertEqual(assess_resume_candidate(paused, available, "true").code,
                         "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")
        pending = replace(paused, provider_outcome_may_be_pending=True)
        self.assertEqual(assess_resume_candidate(pending, available, "false").status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
