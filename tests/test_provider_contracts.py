from __future__ import annotations

import unittest
from dataclasses import replace

from night_shift_pilot.provider_contracts import (
    PROVIDER_CONTRACT_VERSION,
    ExecutionAuthorization,
    ExecutionPolicy,
    InertMockProviderAdapter,
    ProviderCapability,
    ProviderError,
    ProviderExecutionRequest,
)


def capability(**overrides) -> ProviderCapability:
    base = ProviderCapability(
        PROVIDER_CONTRACT_VERSION, "codex-design-mock", "synthetic-model-v1", True,
        frozenset({"documentation"}), frozenset({"none"}), "synthetic-unit", 0, 1,
        30, "not-applicable", "synthetic fixture", ("no-network",),
    )
    return replace(base, **overrides)


def request(**overrides) -> ProviderExecutionRequest:
    base = ProviderExecutionRequest(
        PROVIDER_CONTRACT_VERSION, "request-1", "synthetic-documentation-check-v1",
        "emielpegge/kaya-night-shift-pilot", "documentation", "codex-design-mock",
        "synthetic-model-v1", "MOCK_ONLY", "synthetic-input-digest", 0, "synthetic-unit", 30,
    )
    return replace(base, **overrides)


def authorization(**overrides) -> ExecutionAuthorization:
    return replace(ExecutionAuthorization(PROVIDER_CONTRACT_VERSION, True, False, "synthetic-approval"), **overrides)


def policy(**overrides) -> ExecutionPolicy:
    base = ExecutionPolicy(
        PROVIDER_CONTRACT_VERSION, False, frozenset({"codex-design-mock"}),
        frozenset({"synthetic-documentation-check-v1"}),
        frozenset({"emielpegge/kaya-night-shift-pilot"}), 0, 0, "synthetic-unit", 30, 1,
    )
    return replace(base, **overrides)


class ProviderContractSafetyTests(unittest.TestCase):
    def execute(self, **overrides):
        return InertMockProviderAdapter(overrides.pop("capability", capability())).execute(
            overrides.pop("request", request()), overrides.pop("authorization", authorization()),
            overrides.pop("policy", policy()), overrides.pop("emergency_stop", "false"))

    def assert_denied(self, result, code):
        self.assertEqual(result.status, "DENIED")
        self.assertIsInstance(result.error, ProviderError)
        self.assertEqual(result.error.code, code)

    def test_valid_mock_only_contract_is_inert_and_deterministic(self):
        first = self.execute()
        second = self.execute()
        self.assertEqual(first, second)
        self.assertEqual(first.status, "MOCK_COMPLETED")
        self.assertEqual(first.usage.declared_cost, 0)
        self.assertEqual(first.audit_metadata, (("adapter", "inert-mock"), ("execution", "mock-only")))

    def test_live_execution_is_always_disabled_even_with_hypothetical_approval(self):
        result = self.execute(request=request(execution_mode="LIVE"), authorization=authorization(paid_call_approved=True),
            policy=policy(live_execution_enabled=True))
        self.assert_denied(result, "LIVE_PROVIDER_EXECUTION_DISABLED")

    def test_missing_authorization_invalid_provider_budget_and_allowlists_block(self):
        self.assert_denied(self.execute(authorization=authorization(provider_use_approved=False)), "PROVIDER_USE_NOT_APPROVED")
        self.assert_denied(self.execute(request=request(provider_id="unknown", model_id="other")), "PROVIDER_IDENTITY_MISMATCH")
        self.assert_denied(self.execute(request=request(maximum_cost=1)), "BUDGET_NOT_AUTHORIZED")
        self.assert_denied(self.execute(request=request(task_id="other")), "TASK_OR_REPOSITORY_NOT_ALLOWLISTED")
        self.assert_denied(self.execute(request=request(repository="other/repository")), "TASK_OR_REPOSITORY_NOT_ALLOWLISTED")
        self.assert_denied(self.execute(request=request(task_kind="backend")), "TASK_KIND_UNSUPPORTED")

    def test_paid_mock_contract_requires_separate_paid_approval(self):
        paid_request = request(maximum_cost=1)
        paid_policy = policy(maximum_cost_per_task=1, maximum_cost_per_night=1)
        self.assert_denied(self.execute(request=paid_request, policy=paid_policy,
            capability=capability(maximum_declared_cost=1)), "PAID_CALL_NOT_APPROVED")

    def test_active_emergency_stop_and_non_mock_provider_block(self):
        self.assert_denied(self.execute(emergency_stop="true"), "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")
        adapter = InertMockProviderAdapter(capability(mock_only=False))
        result = adapter.execute(request(), authorization(), policy(), "false")
        self.assert_denied(result, "NON_MOCK_PROVIDER_BLOCKED")

    def test_invalid_contract_or_timeout_blocks_without_execution(self):
        self.assert_denied(self.execute(request=request(contract_version="other")), "EXECUTION_REQUEST_INVALID")
        self.assert_denied(self.execute(request=request(timeout_seconds=31)), "TIMEOUT_NOT_AUTHORIZED")

    def test_malformed_inputs_always_return_structured_denials(self):
        cases = (
            ("none", {"request": None}, "EXECUTION_REQUEST_INVALID"),
            ("wrong-request-type", {"request": []}, "EXECUTION_REQUEST_INVALID"),
            ("missing-request-value", {"request": request(request_id="")}, "EXECUTION_REQUEST_INVALID"),
            ("invalid-request-number", {"request": request(maximum_cost=True)}, "EXECUTION_REQUEST_INVALID"),
            ("invalid-capability-object", {"capability": object()}, "PROVIDER_CAPABILITY_INVALID"),
            ("invalid-capability-value", {"capability": capability(maximum_capacity=True)}, "PROVIDER_CAPABILITY_INVALID"),
            ("invalid-authorization", {"authorization": None}, "EXECUTION_AUTHORIZATION_MISSING"),
            ("invalid-policy", {"policy": None}, "EXECUTION_POLICY_INVALID"),
            ("invalid-policy-number", {"policy": policy(maximum_cost_per_task=True)}, "EXECUTION_POLICY_INVALID"),
        )
        for label, overrides, code in cases:
            with self.subTest(label=label):
                self.assert_denied(self.execute(**overrides), code)

    def test_static_cost_unit_limits_capacity_and_timeout_contracts_block(self):
        self.assert_denied(self.execute(request=request(cost_unit="other")), "COST_UNIT_MISMATCH")
        self.assert_denied(self.execute(capability=capability(cost_unit="other")), "COST_UNIT_MISMATCH")
        self.assert_denied(self.execute(request=request(maximum_cost=1), policy=policy(maximum_cost_per_task=1,
            maximum_cost_per_night=0)), "BUDGET_NOT_AUTHORIZED")
        self.assert_denied(self.execute(capability=capability(maximum_capacity=0)), "CAPACITY_UNAVAILABLE_STATIC")
        self.assert_denied(self.execute(capability=capability(timeout_seconds=29)), "TIMEOUT_NOT_AUTHORIZED")


if __name__ == "__main__":
    unittest.main()
