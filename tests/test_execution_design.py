from __future__ import annotations

import unittest
from dataclasses import replace

from night_shift_pilot.execution_design import (
    EXECUTION_DESIGN_VERSION, AccountingState, ExecutionGrant, GrantPolicy, Reservation,
    authorize_live_execution, authorize_publication, commit_provider_cost, mark_provider_outcome_unknown,
    mark_provider_start_may_have_occurred, record_crash_before_reservation, release_pre_start_reservation,
    reserve_budget, validate_grant,
)


SHA = "a" * 64


def policy(**overrides) -> GrantPolicy:
    base = GrantPolicy(EXECUTION_DESIGN_VERSION, "synthetic-policy-v1",
        frozenset({("openai-codex", "model-to-verify-later")}),
        frozenset({"example/private-synthetic-pilot"}), frozenset({"refs/heads/approved"}),
        frozenset({"synthetic-task-v1"}), 10, 60)
    return replace(base, **overrides)


def grant(**overrides) -> ExecutionGrant:
    base = ExecutionGrant(EXECUTION_DESIGN_VERSION, "synthetic-task-v1", SHA, "openai-codex",
        "model-to-verify-later", "example/private-synthetic-pilot", "refs/heads/approved",
        "synthetic-policy-v1", True, True, 5, "synthetic-cost-model-v1", 30, 10, 20,
        "request-1", "idempotency-1", "synthetic-human-approval")
    return replace(base, **overrides)


def state(**overrides) -> AccountingState:
    return replace(AccountingState("synthetic-cost-model-v1", 10, 2, 1), **overrides)


class ExecutionDesignTests(unittest.TestCase):
    def test_valid_grant_is_only_valid_for_future_boundary_and_live_is_denied(self):
        self.assertEqual(validate_grant(grant(), policy(), 15).status, "VALID_FOR_FUTURE_PRIVATE_BOUNDARY")
        self.assertEqual(authorize_live_execution(grant(), policy(), 15, "false").code, "LIVE_EXECUTION_NOT_IMPLEMENTED")

    def test_grant_authorization_expiry_digest_scope_and_cost_guards(self):
        cases = (
            (grant(provider_approved=False), "EXECUTION_GRANT_APPROVAL_MISSING"),
            (grant(expires_at_epoch=15), "EXECUTION_GRANT_EXPIRED"),
            (grant(task_artifact_sha256="bad"), "EXECUTION_GRANT_INVALID"),
            (grant(model_id="other"), "EXECUTION_GRANT_SCOPE_MISMATCH"),
            (grant(repository="other/repo"), "EXECUTION_GRANT_SCOPE_MISMATCH"),
            (grant(ref="refs/heads/main"), "EXECUTION_GRANT_SCOPE_MISMATCH"),
            (grant(cost_model_id=None), "COST_MODEL_UNKNOWN"),
            (grant(maximum_cost=11), "TASK_BUDGET_EXCEEDED"),
            (grant(maximum_duration_seconds=61), "EXECUTION_TIMEOUT_INVALID"),
            (grant(provider_approved=1), "EXECUTION_GRANT_INVALID"),
            (grant(issued_at_epoch=16), "EXECUTION_GRANT_NOT_YET_VALID"),
            (grant(policy_version="other"), "POLICY_VERSION_MISMATCH"),
        )
        for item, code in cases:
            with self.subTest(code=code):
                self.assertEqual(validate_grant(item, policy(), 15).code, code)

    def test_stop_always_wins_and_no_live_path_exists(self):
        self.assertEqual(authorize_live_execution(grant(), policy(), 15, "true").code,
            "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")
        self.assertEqual(authorize_live_execution(grant(), policy(), 15, None).status, "DENIED")

    def test_reservation_rejects_unknown_cost_and_night_budget_overrun(self):
        self.assertEqual(reserve_budget(state(cost_model_id=None), grant(), policy(), 15).code, "COST_MODEL_UNKNOWN")
        self.assertEqual(reserve_budget(state(nightly_budget=4), grant(), policy(), 15).code, "NIGHTLY_BUDGET_EXCEEDED")

    def test_duplicate_and_idempotency_replay_are_blocked(self):
        reserved = reserve_budget(state(), grant(), policy(), 15).state
        self.assertEqual(reserve_budget(reserved, grant(), policy(), 15).code, "DUPLICATE_REQUEST_ID")
        replay = grant(request_id="request-2")
        self.assertEqual(reserve_budget(reserved, replay, policy(), 15).code, "IDEMPOTENCY_REPLAY_BLOCKED")

    def test_rate_and_concurrency_limits_block_before_future_execution(self):
        first = reserve_budget(state(maximum_concurrency=1), grant(), policy(), 15).state
        second = grant(request_id="request-2", idempotency_key="idempotency-2")
        self.assertEqual(reserve_budget(first, second, policy(), 15).code, "CONCURRENCY_LIMIT_EXCEEDED")
        exhausted = reserve_budget(state(maximum_requests=1, maximum_concurrency=2), grant(), policy(), 15).state
        self.assertEqual(reserve_budget(exhausted, second, policy(), 15).code, "RATE_LIMIT_EXCEEDED")

    def test_committed_cost_remains_in_cumulative_night_budget(self):
        first = reserve_budget(state(nightly_budget=10, maximum_concurrency=2), grant(maximum_cost=6), policy(), 15).state
        started = mark_provider_start_may_have_occurred(first, "request-1").state
        committed = commit_provider_cost(started, "request-1", 6).state
        second = grant(request_id="request-2", idempotency_key="idempotency-2", maximum_cost=5)
        self.assertEqual(reserve_budget(committed, second, policy(), 15).code, "NIGHTLY_BUDGET_EXCEEDED")
        allowed = grant(request_id="request-3", idempotency_key="idempotency-3", maximum_cost=4)
        self.assertEqual(reserve_budget(committed, allowed, policy(), 15).status, "RESERVED_FOR_FUTURE_PRIVATE_EXECUTION")

    def test_crash_before_start_can_release_but_unknown_outcome_remains_reserved(self):
        initial = state()
        pre_reservation_crash = record_crash_before_reservation(initial)
        self.assertEqual(pre_reservation_crash.code, "CRASH_BEFORE_RESERVATION_NO_EXECUTION")
        self.assertEqual(pre_reservation_crash.state, initial)
        reserved = reserve_budget(state(), grant(), policy(), 15).state
        possible_start = mark_provider_start_may_have_occurred(reserved, "request-1")
        self.assertEqual(release_pre_start_reservation(possible_start.state, "request-1").code, "PRE_START_EVIDENCE_REQUIRED")
        self.assertEqual(commit_provider_cost(reserved, "request-1", 1).code, "INVALID_COMMIT_TRANSITION")
        released = release_pre_start_reservation(reserved, "request-1")
        self.assertEqual(released.status, "RELEASED")
        self.assertEqual(released.state.reservations[0].state, "RELEASED_PRE_START")
        reserved = reserve_budget(state(), grant(), policy(), 15).state
        unknown = mark_provider_outcome_unknown(reserved, "request-1")
        self.assertEqual(unknown.status, "UNKNOWN_PROVIDER_OUTCOME")
        self.assertEqual(unknown.state.reservations[0].state, "UNKNOWN_PROVIDER_OUTCOME")
        self.assertEqual(release_pre_start_reservation(unknown.state, "request-1").status, "DENIED")

    def test_invalid_policy_and_reservation_records_fail_closed(self):
        self.assertEqual(validate_grant(grant(), policy(maximum_cost_per_task=True), 15).code, "EXECUTION_POLICY_INVALID")
        invalid = state(reservations=(Reservation("request-1", "idem", -1, "UNKNOWN", "PRE_START_CONFIRMED"),))
        self.assertEqual(reserve_budget(invalid, grant(), policy(), 15).code, "ACCOUNTING_STATE_INVALID")
        self.assertEqual(release_pre_start_reservation(invalid, "request-1").code, "ACCOUNTING_STATE_INVALID")

    def test_publication_is_never_authorized_by_a_provider_or_grant_result(self):
        self.assertEqual(authorize_publication().code, "PUBLICATION_REQUIRES_SEPARATE_HUMAN_APPROVAL")


if __name__ == "__main__":
    unittest.main()
