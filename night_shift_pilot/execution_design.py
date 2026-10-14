"""Pure, inert v0.5 contracts for a future private Codex execution boundary.

No provider client, credential, environment lookup, network transport, clock,
or live executor exists here.  `authorize_live_execution` always denies.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


EXECUTION_DESIGN_VERSION = "night-shift-execution-design-v0.5"


@dataclass(frozen=True)
class ExecutionGrant:
    contract_version: str
    task_id: str
    task_artifact_sha256: str
    provider_id: str
    model_id: str
    repository: str
    ref: str
    policy_version: str
    provider_approved: bool
    paid_approved: bool
    maximum_cost: int
    cost_model_id: str | None
    maximum_duration_seconds: int
    issued_at_epoch: int
    expires_at_epoch: int
    request_id: str
    idempotency_key: str
    human_approval_reference: str


@dataclass(frozen=True)
class GrantPolicy:
    contract_version: str
    policy_version: str
    allowed_provider_models: frozenset[tuple[str, str]]
    allowed_repositories: frozenset[str]
    allowed_refs: frozenset[str]
    allowed_task_ids: frozenset[str]
    maximum_cost_per_task: int
    maximum_duration_seconds: int


@dataclass(frozen=True)
class GrantDecision:
    status: str
    code: str


@dataclass(frozen=True)
class Reservation:
    request_id: str
    idempotency_key: str
    reserved_cost: int
    state: str  # RESERVED, COMMITTED, UNKNOWN_PROVIDER_OUTCOME, RELEASED_PRE_START
    provider_start_status: str  # PRE_START_CONFIRMED, START_MAY_HAVE_OCCURRED, START_CONFIRMED
    committed_cost: int | None = None


@dataclass(frozen=True)
class AccountingState:
    cost_model_id: str | None
    nightly_budget: int
    maximum_requests: int
    maximum_concurrency: int
    reservations: tuple[Reservation, ...] = ()


@dataclass(frozen=True)
class AccountingDecision:
    status: str
    code: str
    state: AccountingState


@dataclass(frozen=True)
class FutureExecutionAudit:
    contract_version: str
    task_id: str
    request_id: str
    provider_id: str
    model_id: str
    output_sha256: str | None
    result_status: str
    test_status: str
    usage_status: str
    review_status: str
    error_code: str | None


def _nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _string_set(value: object) -> bool:
    return isinstance(value, frozenset) and all(_text(item) for item in value)


def _validate_policy(policy: object) -> str | None:
    if not isinstance(policy, GrantPolicy) or policy.contract_version != EXECUTION_DESIGN_VERSION:
        return "EXECUTION_POLICY_INVALID"
    pairs_valid = isinstance(policy.allowed_provider_models, frozenset) and all(
        isinstance(pair, tuple) and len(pair) == 2 and all(_text(item) for item in pair)
        for pair in policy.allowed_provider_models)
    if (not _text(policy.policy_version) or not pairs_valid or not _string_set(policy.allowed_repositories) or
            not _string_set(policy.allowed_refs) or not _string_set(policy.allowed_task_ids) or
            not _nonnegative_int(policy.maximum_cost_per_task) or
            not isinstance(policy.maximum_duration_seconds, int) or isinstance(policy.maximum_duration_seconds, bool) or
            policy.maximum_duration_seconds < 1):
        return "EXECUTION_POLICY_INVALID"
    return None


def _validate_accounting_state(state: object) -> str | None:
    if (not isinstance(state, AccountingState) or
            (state.cost_model_id is not None and not _text(state.cost_model_id)) or
            not _nonnegative_int(state.nightly_budget) or not _nonnegative_int(state.maximum_requests) or
            not _nonnegative_int(state.maximum_concurrency) or not isinstance(state.reservations, tuple)):
        return "ACCOUNTING_STATE_INVALID"
    request_ids: set[str] = set()
    idempotency_keys: set[str] = set()
    states = {"RESERVED", "COMMITTED", "UNKNOWN_PROVIDER_OUTCOME", "RELEASED_PRE_START"}
    starts = {"PRE_START_CONFIRMED", "START_MAY_HAVE_OCCURRED", "START_CONFIRMED"}
    for item in state.reservations:
        if (not isinstance(item, Reservation) or not _text(item.request_id) or not _text(item.idempotency_key) or
                not _nonnegative_int(item.reserved_cost) or item.state not in states or
                item.provider_start_status not in starts or item.request_id in request_ids or
                item.idempotency_key in idempotency_keys):
            return "ACCOUNTING_STATE_INVALID"
        if item.state == "COMMITTED":
            if not _nonnegative_int(item.committed_cost) or item.committed_cost > item.reserved_cost:
                return "ACCOUNTING_STATE_INVALID"
        elif item.committed_cost is not None:
            return "ACCOUNTING_STATE_INVALID"
        if item.state == "RELEASED_PRE_START" and item.provider_start_status != "PRE_START_CONFIRMED":
            return "ACCOUNTING_STATE_INVALID"
        request_ids.add(item.request_id)
        idempotency_keys.add(item.idempotency_key)
    return None


def _nightly_blocked_cost(reservations: tuple[Reservation, ...]) -> int:
    """Committed spend and all potentially chargeable reservations retain budget."""
    return sum(item.committed_cost if item.state == "COMMITTED" else item.reserved_cost
        for item in reservations if item.state != "RELEASED_PRE_START")


def validate_grant(grant: object, policy: object, now_epoch: object) -> GrantDecision:
    """Validate a proposed grant without issuing credentials or authorizing execution."""
    if not isinstance(grant, ExecutionGrant) or grant.contract_version != EXECUTION_DESIGN_VERSION:
        return GrantDecision("DENIED", "EXECUTION_GRANT_INVALID")
    policy_error = _validate_policy(policy)
    if policy_error:
        return GrantDecision("DENIED", policy_error)
    if not _nonnegative_int(now_epoch):
        return GrantDecision("DENIED", "CLOCK_INVALID")
    text_fields = (grant.task_id, grant.provider_id, grant.model_id, grant.repository, grant.ref,
        grant.policy_version, grant.request_id, grant.idempotency_key, grant.human_approval_reference)
    if (not all(_text(value) for value in text_fields) or not _sha256(grant.task_artifact_sha256) or
            not _nonnegative_int(grant.maximum_cost) or not _nonnegative_int(grant.maximum_duration_seconds) or
            not _nonnegative_int(grant.issued_at_epoch) or not _nonnegative_int(grant.expires_at_epoch) or
            grant.expires_at_epoch <= grant.issued_at_epoch or not isinstance(grant.provider_approved, bool) or
            not isinstance(grant.paid_approved, bool)):
        return GrantDecision("DENIED", "EXECUTION_GRANT_INVALID")
    if grant.policy_version != policy.policy_version:
        return GrantDecision("DENIED", "POLICY_VERSION_MISMATCH")
    if now_epoch >= grant.expires_at_epoch:
        return GrantDecision("DENIED", "EXECUTION_GRANT_EXPIRED")
    if grant.issued_at_epoch > now_epoch:
        return GrantDecision("DENIED", "EXECUTION_GRANT_NOT_YET_VALID")
    if not grant.provider_approved or not grant.paid_approved:
        return GrantDecision("DENIED", "EXECUTION_GRANT_APPROVAL_MISSING")
    if grant.cost_model_id is None or not _text(grant.cost_model_id):
        return GrantDecision("DENIED", "COST_MODEL_UNKNOWN")
    if ((grant.provider_id, grant.model_id) not in policy.allowed_provider_models or
            grant.repository not in policy.allowed_repositories or grant.ref not in policy.allowed_refs or
            grant.task_id not in policy.allowed_task_ids):
        return GrantDecision("DENIED", "EXECUTION_GRANT_SCOPE_MISMATCH")
    if grant.maximum_cost > policy.maximum_cost_per_task:
        return GrantDecision("DENIED", "TASK_BUDGET_EXCEEDED")
    if grant.maximum_duration_seconds < 1 or grant.maximum_duration_seconds > policy.maximum_duration_seconds:
        return GrantDecision("DENIED", "EXECUTION_TIMEOUT_INVALID")
    return GrantDecision("VALID_FOR_FUTURE_PRIVATE_BOUNDARY", "GRANT_VALIDATION_ONLY")


def authorize_live_execution(grant: object, policy: object, now_epoch: object,
                             emergency_stop: str | None) -> GrantDecision:
    """v0.5's non-bypassable boundary: live execution has no implementation."""
    if emergency_stop != "false":
        return GrantDecision("DENIED", "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")
    decision = validate_grant(grant, policy, now_epoch)
    if decision.status != "VALID_FOR_FUTURE_PRIVATE_BOUNDARY":
        return decision
    return GrantDecision("DENIED", "LIVE_EXECUTION_NOT_IMPLEMENTED")


def reserve_budget(state: object, grant: object, policy: object, now_epoch: object) -> AccountingDecision:
    """Offline state-machine model; it never starts a provider request."""
    validation = validate_grant(grant, policy, now_epoch)
    if validation.status != "VALID_FOR_FUTURE_PRIVATE_BOUNDARY":
        return AccountingDecision("DENIED", validation.code, state if isinstance(state, AccountingState) else _empty_state())
    state_error = _validate_accounting_state(state)
    if state_error:
        return AccountingDecision("DENIED", "ACCOUNTING_STATE_INVALID", state if isinstance(state, AccountingState) else _empty_state())
    if state.cost_model_id != grant.cost_model_id:
        return AccountingDecision("DENIED", "COST_MODEL_UNKNOWN", state)
    if any(item.request_id == grant.request_id for item in state.reservations):
        return AccountingDecision("DENIED", "DUPLICATE_REQUEST_ID", state)
    if any(item.idempotency_key == grant.idempotency_key for item in state.reservations):
        return AccountingDecision("DENIED", "IDEMPOTENCY_REPLAY_BLOCKED", state)
    active = tuple(item for item in state.reservations if item.state in {"RESERVED", "UNKNOWN_PROVIDER_OUTCOME"})
    if len(state.reservations) >= state.maximum_requests:
        return AccountingDecision("DENIED", "RATE_LIMIT_EXCEEDED", state)
    if len(active) >= state.maximum_concurrency:
        return AccountingDecision("DENIED", "CONCURRENCY_LIMIT_EXCEEDED", state)
    if _nightly_blocked_cost(state.reservations) + grant.maximum_cost > state.nightly_budget:
        return AccountingDecision("DENIED", "NIGHTLY_BUDGET_EXCEEDED", state)
    reservation = Reservation(grant.request_id, grant.idempotency_key, grant.maximum_cost, "RESERVED", "PRE_START_CONFIRMED")
    return AccountingDecision("RESERVED_FOR_FUTURE_PRIVATE_EXECUTION", "RESERVATION_CREATED",
        replace(state, reservations=state.reservations + (reservation,)))


def mark_provider_outcome_unknown(state: AccountingState, request_id: str) -> AccountingDecision:
    """Timeout/crash after start retains budget until a human/system reconciliation."""
    if _validate_accounting_state(state):
        return AccountingDecision("DENIED", "ACCOUNTING_STATE_INVALID", state)
    if not _text(request_id):
        return AccountingDecision("DENIED", "REQUEST_ID_INVALID", state)
    changed = False
    reservations = []
    for item in state.reservations:
        if item.request_id == request_id and item.state == "RESERVED":
            reservations.append(replace(item, state="UNKNOWN_PROVIDER_OUTCOME", provider_start_status="START_MAY_HAVE_OCCURRED"))
            changed = True
        else:
            reservations.append(item)
    return AccountingDecision("UNKNOWN_PROVIDER_OUTCOME" if changed else "DENIED",
        "RECONCILIATION_REQUIRED" if changed else "RESERVATION_NOT_FOUND", replace(state, reservations=tuple(reservations)))


def release_pre_start_reservation(state: AccountingState, request_id: str) -> AccountingDecision:
    """Only a confirmed pre-start crash can release a reservation automatically."""
    if _validate_accounting_state(state):
        return AccountingDecision("DENIED", "ACCOUNTING_STATE_INVALID", state)
    changed = False
    reservations = []
    for item in state.reservations:
        if (item.request_id == request_id and item.state == "RESERVED" and
                item.provider_start_status == "PRE_START_CONFIRMED"):
            reservations.append(replace(item, state="RELEASED_PRE_START"))
            changed = True
        else:
            reservations.append(item)
    return AccountingDecision("RELEASED" if changed else "DENIED",
        "PRE_START_RESERVATION_RELEASED" if changed else "PRE_START_EVIDENCE_REQUIRED", replace(state, reservations=tuple(reservations)))


def mark_provider_start_may_have_occurred(state: AccountingState, request_id: str) -> AccountingDecision:
    """Persist this transition before any future provider-start attempt."""
    if _validate_accounting_state(state):
        return AccountingDecision("DENIED", "ACCOUNTING_STATE_INVALID", state)
    changed = False
    reservations = []
    for item in state.reservations:
        if item.request_id == request_id and item.state == "RESERVED" and item.provider_start_status == "PRE_START_CONFIRMED":
            reservations.append(replace(item, provider_start_status="START_MAY_HAVE_OCCURRED"))
            changed = True
        else:
            reservations.append(item)
    return AccountingDecision("START_MAY_HAVE_OCCURRED" if changed else "DENIED",
        "PROVIDER_START_BOUNDARY_RECORDED" if changed else "INVALID_PROVIDER_START_TRANSITION",
        replace(state, reservations=tuple(reservations)))


def commit_provider_cost(state: AccountingState, request_id: str, actual_cost: object) -> AccountingDecision:
    """Pure reconciliation transition; does not contact a provider or release budget."""
    if _validate_accounting_state(state):
        return AccountingDecision("DENIED", "ACCOUNTING_STATE_INVALID", state)
    if not _nonnegative_int(actual_cost):
        return AccountingDecision("DENIED", "COMMITTED_COST_INVALID", state)
    changed = False
    reservations = []
    for item in state.reservations:
        if (item.request_id == request_id and item.state == "RESERVED" and
                item.provider_start_status in {"START_MAY_HAVE_OCCURRED", "START_CONFIRMED"}):
            if actual_cost > item.reserved_cost:
                return AccountingDecision("DENIED", "COMMITTED_COST_EXCEEDS_RESERVATION", state)
            reservations.append(replace(item, state="COMMITTED", committed_cost=actual_cost))
            changed = True
        else:
            reservations.append(item)
    return AccountingDecision("COMMITTED" if changed else "DENIED",
        "PROVIDER_COST_COMMITTED" if changed else "INVALID_COMMIT_TRANSITION", replace(state, reservations=tuple(reservations)))


def record_crash_before_reservation(state: AccountingState) -> AccountingDecision:
    """Pure crash model: before reservation there is nothing to release or execute."""
    return AccountingDecision("BLOCKED", "CRASH_BEFORE_RESERVATION_NO_EXECUTION", state)


def authorize_publication() -> GrantDecision:
    """AI/provider output can never publish automatically in this design phase."""
    return GrantDecision("DENIED", "PUBLICATION_REQUIRES_SEPARATE_HUMAN_APPROVAL")


def _empty_state() -> AccountingState:
    return AccountingState(None, 0, 0, 0)
