"""Inert v0.4 contracts for a future real-provider boundary.

There are deliberately no SDK imports, credentials, provider URLs, environment
variables, or network clients in this module.  A live request is always denied.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


PROVIDER_CONTRACT_VERSION = "night-shift-provider-contract-v0.4"
ExecutionMode = Literal["MOCK_ONLY", "LIVE"]
AuthorizationStatus = Literal["ALLOWED_MOCK_ONLY", "DENIED"]


@dataclass(frozen=True)
class ProviderCapability:
    contract_version: str
    provider_id: str
    model_id: str
    mock_only: bool
    supported_task_kinds: frozenset[str]
    authentication_methods: frozenset[str]
    cost_unit: str
    maximum_declared_cost: int | None
    maximum_capacity: int
    timeout_seconds: int
    rate_limit_description: str
    quality_description: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ProviderExecutionRequest:
    contract_version: str
    request_id: str
    task_id: str
    repository: str
    task_kind: str
    provider_id: str
    model_id: str
    execution_mode: ExecutionMode
    input_digest: str
    maximum_cost: int
    cost_unit: str
    timeout_seconds: int


@dataclass(frozen=True)
class ProviderUsage:
    contract_version: str
    cost_unit: str
    declared_cost: int | None
    provider_request_id: str | None


@dataclass(frozen=True)
class ProviderError:
    contract_version: str
    code: str
    retryable: bool
    public_detail: str


@dataclass(frozen=True)
class ProviderExecutionResult:
    contract_version: str
    status: Literal["MOCK_COMPLETED", "DENIED", "FAILED"]
    request_id: str
    provider_id: str
    model_id: str
    output_digest: str | None
    usage: ProviderUsage | None
    error: ProviderError | None
    audit_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ExecutionAuthorization:
    contract_version: str
    provider_use_approved: bool
    paid_call_approved: bool
    approval_reference: str | None


@dataclass(frozen=True)
class ExecutionPolicy:
    contract_version: str
    live_execution_enabled: bool
    allowed_provider_ids: frozenset[str]
    allowed_task_ids: frozenset[str]
    allowed_repositories: frozenset[str]
    maximum_cost_per_task: int
    maximum_cost_per_night: int
    cost_unit: str
    maximum_timeout_seconds: int
    maximum_rate_per_night: int


class ProviderAdapter(Protocol):
    """Future adapter seam. v0.4 supplies only an inert mock implementation."""

    capability: ProviderCapability

    def execute(self, request: ProviderExecutionRequest,
                authorization: ExecutionAuthorization,
                policy: ExecutionPolicy,
                emergency_stop: str | None) -> ProviderExecutionResult: ...


def _valid_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _valid_nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def authorize_execution(request: object, capability: object, authorization: object,
                        policy: object, emergency_stop: str | None) -> ExecutionAuthorization | ProviderError:
    """Evaluate a future request without executing it; all live paths fail closed."""
    if emergency_stop != "false":
        return ProviderError(PROVIDER_CONTRACT_VERSION, "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE", False, "execution blocked")
    if not isinstance(request, ProviderExecutionRequest) or request.contract_version != PROVIDER_CONTRACT_VERSION:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "EXECUTION_REQUEST_INVALID", False, "execution blocked")
    if not isinstance(capability, ProviderCapability) or capability.contract_version != PROVIDER_CONTRACT_VERSION:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "PROVIDER_CAPABILITY_INVALID", False, "execution blocked")
    if not isinstance(authorization, ExecutionAuthorization) or authorization.contract_version != PROVIDER_CONTRACT_VERSION:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "EXECUTION_AUTHORIZATION_MISSING", False, "execution blocked")
    if not isinstance(policy, ExecutionPolicy) or policy.contract_version != PROVIDER_CONTRACT_VERSION:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "EXECUTION_POLICY_INVALID", False, "execution blocked")
    required_strings = (request.request_id, request.task_id, request.repository, request.task_kind,
        request.provider_id, request.model_id, request.input_digest, request.cost_unit)
    if (not all(_valid_string(value) for value in required_strings) or
            not _valid_nonnegative_int(request.maximum_cost) or
            not isinstance(request.timeout_seconds, int) or isinstance(request.timeout_seconds, bool) or
            not isinstance(request.execution_mode, str) or request.execution_mode not in {"MOCK_ONLY", "LIVE"}):
        return ProviderError(PROVIDER_CONTRACT_VERSION, "EXECUTION_REQUEST_INVALID", False, "execution blocked")
    if request.provider_id != capability.provider_id or request.model_id != capability.model_id:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "PROVIDER_IDENTITY_MISMATCH", False, "execution blocked")
    if request.provider_id not in policy.allowed_provider_ids:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "PROVIDER_NOT_ALLOWLISTED", False, "execution blocked")
    if request.task_kind not in capability.supported_task_kinds:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "TASK_KIND_UNSUPPORTED", False, "execution blocked")
    if request.task_id not in policy.allowed_task_ids or request.repository not in policy.allowed_repositories:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "TASK_OR_REPOSITORY_NOT_ALLOWLISTED", False, "execution blocked")
    if request.cost_unit != policy.cost_unit or request.maximum_cost > policy.maximum_cost_per_task:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "BUDGET_NOT_AUTHORIZED", False, "execution blocked")
    if request.timeout_seconds < 1 or request.timeout_seconds > policy.maximum_timeout_seconds:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "TIMEOUT_NOT_AUTHORIZED", False, "execution blocked")
    if not authorization.provider_use_approved:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "PROVIDER_USE_NOT_APPROVED", False, "execution blocked")
    if request.maximum_cost > 0 and not authorization.paid_call_approved:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "PAID_CALL_NOT_APPROVED", False, "execution blocked")
    if request.execution_mode != "MOCK_ONLY":
        return ProviderError(PROVIDER_CONTRACT_VERSION, "LIVE_PROVIDER_EXECUTION_DISABLED", False, "execution blocked")
    if not capability.mock_only:
        return ProviderError(PROVIDER_CONTRACT_VERSION, "NON_MOCK_PROVIDER_BLOCKED", False, "execution blocked")
    return ExecutionAuthorization(PROVIDER_CONTRACT_VERSION, True, authorization.paid_call_approved,
        authorization.approval_reference)


class InertMockProviderAdapter:
    """Test double that returns a deterministic marker and cannot contact a provider."""

    def __init__(self, capability: ProviderCapability):
        self.capability = capability

    def execute(self, request: ProviderExecutionRequest, authorization: ExecutionAuthorization,
                policy: ExecutionPolicy, emergency_stop: str | None) -> ProviderExecutionResult:
        decision = authorize_execution(request, self.capability, authorization, policy, emergency_stop)
        if isinstance(decision, ProviderError):
            return ProviderExecutionResult(PROVIDER_CONTRACT_VERSION, "DENIED", request.request_id,
                request.provider_id, request.model_id, None, None, decision,
                (("adapter", "inert-mock"),))
        return ProviderExecutionResult(PROVIDER_CONTRACT_VERSION, "MOCK_COMPLETED", request.request_id,
            request.provider_id, request.model_id, "synthetic-output-not-provider-generated",
            ProviderUsage(PROVIDER_CONTRACT_VERSION, request.cost_unit, 0, None), None,
            (("adapter", "inert-mock"), ("execution", "mock-only")))
