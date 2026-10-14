"""Inert v0.7 quota normalization, recheck planning, and checkpoint contracts.

No App Server process, account token, scheduler, timer, provider request, or
model execution is implemented here.  These contracts are deliberately stricter
than a parsed JSON payload: a future connector must attest trusted origin.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from math import isfinite


QUOTA_CONTRACT_VERSION = "subscription-quota-v0.7"
MAXIMUM_EVIDENCE_AGE_SECONDS = 300
RECHECK_DELAY_SECONDS = 5
MAX_RECHECK_ATTEMPTS = 5
MAX_RECHECK_BACKOFF_SECONDS = 900
READ_ONLY_APP_SERVER_METHODS = frozenset({"account/read", "account/rateLimits/read"})
READ_ONLY_APP_SERVER_NOTIFICATIONS = frozenset({"account/rateLimits/updated"})
FORBIDDEN_APP_SERVER_METHODS = frozenset({
    "account/login/start", "account/login/cancel", "account/logout",
    "account/rateLimitResetCredit/consume", "account/sendAddCreditsNudgeEmail",
    "account/usage/read",
})


@dataclass(frozen=True)
class QuotaWindow:
    used_percent: int | float
    window_duration_mins: int
    resets_at_epoch: int


@dataclass(frozen=True)
class QuotaBucket:
    limit_id: str
    primary: QuotaWindow | None
    secondary: QuotaWindow | None
    rate_limit_reached_type: str | None


@dataclass(frozen=True)
class BucketRequirement:
    limit_id: str
    logical_limit: str  # five_hour or weekly; configured from later official evidence
    secondary_required: bool
    known_reached_types: frozenset[str]


@dataclass(frozen=True)
class ProviderQuotaContract:
    contract_version: str
    provider_id: str
    expected_auth_mode: str
    required_buckets: tuple[BucketRequirement, ...]
    maximum_evidence_age_seconds: int = MAXIMUM_EVIDENCE_AGE_SECONDS


@dataclass(frozen=True)
class AppServerQuotaEvidence:
    contract_version: str
    provider_id: str
    access_mode: str
    auth_mode: str
    plan_type: str | None
    observed_at_epoch: int
    source_attested: bool
    rate_limits_by_limit_id: tuple[QuotaBucket, ...]
    legacy_rate_limits: QuotaBucket | None
    reset_credit_count: int | None


@dataclass(frozen=True)
class QuotaDecision:
    state: str
    code: str
    blocking_limits: frozenset[str]
    relevant_resets_at: tuple[int, ...]
    source_trusted: bool
    capacity_available: bool
    task_start_authorized: bool = False


@dataclass(frozen=True)
class RecheckPlan:
    checkpoint_id: str
    attempt: int
    scheduled_at_epoch: int
    idempotency_key: str
    status: str


@dataclass(frozen=True)
class TaskCheckpoint:
    checkpoint_id: str
    task_id: str
    task_digest_sha256: str
    provider_id: str
    last_confirmed_checkpoint: str
    execution_status: str
    provider_outcome_may_be_pending: bool
    quota_state: str
    evidence_observed_at_epoch: int | None
    reported_resets_at: tuple[int, ...]
    review_status: str
    continuation_authorized: bool
    execution_attempt_id: str


@dataclass(frozen=True)
class ResumeCandidate:
    status: str
    code: str
    task_start_authorized: bool


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _epoch(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _positive_int(value: object) -> bool:
    return _epoch(value) and value > 0


def _percent(value: object) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and
            isfinite(value) and 0 <= value <= 100)


def _window_valid(window: object, observed_at_epoch: int) -> bool:
    return (isinstance(window, QuotaWindow) and _percent(window.used_percent) and
            _positive_int(window.window_duration_mins) and _epoch(window.resets_at_epoch) and
            window.resets_at_epoch >= observed_at_epoch)


def _contract_valid(contract: object) -> bool:
    if (not isinstance(contract, ProviderQuotaContract) or
            contract.contract_version != QUOTA_CONTRACT_VERSION or not _text(contract.provider_id) or
            contract.expected_auth_mode != "chatgpt" or not _positive_int(contract.maximum_evidence_age_seconds) or
            not isinstance(contract.required_buckets, tuple) or not contract.required_buckets):
        return False
    ids: set[str] = set()
    for item in contract.required_buckets:
        if (not isinstance(item, BucketRequirement) or not _text(item.limit_id) or
                item.logical_limit not in {"five_hour", "weekly"} or
                not isinstance(item.secondary_required, bool) or
                not isinstance(item.known_reached_types, frozenset) or
                not all(_text(value) for value in item.known_reached_types) or item.limit_id in ids):
            return False
        ids.add(item.limit_id)
    return True


def app_server_operation_allowed(operation: object, *, notification: object = False) -> bool:
    """Strict allowlist: read operations/one notification only, never a command."""
    if not isinstance(notification, bool) or not _text(operation):
        return False
    return operation in (READ_ONLY_APP_SERVER_NOTIFICATIONS if notification else READ_ONLY_APP_SERVER_METHODS)


def normalize_codex_quota(evidence: object, contract: object, now_epoch: object) -> QuotaDecision:
    """Validate source, schema and quota interpretation; it grants no task permission."""
    unknown = QuotaDecision("QUOTA_UNKNOWN", "QUOTA_EVIDENCE_INVALID", frozenset(), (), False, False)
    if not _contract_valid(contract) or not _epoch(now_epoch):
        return unknown
    if (not isinstance(evidence, AppServerQuotaEvidence) or evidence.contract_version != QUOTA_CONTRACT_VERSION or
            evidence.provider_id != contract.provider_id or evidence.access_mode != "CHATGPT_SUBSCRIPTION" or
            evidence.auth_mode != contract.expected_auth_mode or not _text(evidence.plan_type) or
            not isinstance(evidence.source_attested, bool) or not evidence.source_attested or
            not _epoch(evidence.observed_at_epoch) or now_epoch < evidence.observed_at_epoch or
            now_epoch - evidence.observed_at_epoch > contract.maximum_evidence_age_seconds or
            not isinstance(evidence.rate_limits_by_limit_id, tuple) or
            (evidence.reset_credit_count is not None and not _epoch(evidence.reset_credit_count))):
        return unknown
    if evidence.reset_credit_count not in {None, 0}:
        return QuotaDecision("MANUAL_REVIEW_REQUIRED", "RESET_CREDIT_PRESENT_FORBIDDEN", frozenset(), (), True, False)
    requirements = {item.limit_id: item for item in contract.required_buckets}
    buckets: dict[str, QuotaBucket] = {}
    for bucket in evidence.rate_limits_by_limit_id:
        if not isinstance(bucket, QuotaBucket) or not _text(bucket.limit_id) or bucket.limit_id in buckets:
            return unknown
        buckets[bucket.limit_id] = bucket
    if set(buckets) != set(requirements):
        return QuotaDecision("QUOTA_UNKNOWN", "REQUIRED_OR_UNKNOWN_BUCKET_MISMATCH", frozenset(), (), True, False)
    if evidence.legacy_rate_limits is not None:
        legacy = evidence.legacy_rate_limits
        if not isinstance(legacy, QuotaBucket) or legacy.limit_id not in buckets or legacy != buckets[legacy.limit_id]:
            return QuotaDecision("QUOTA_UNKNOWN", "LEGACY_BUCKET_CONFLICT", frozenset(), (), True, False)
    blocking: set[str] = set()
    resets: set[int] = set()
    for limit_id, requirement in requirements.items():
        bucket = buckets[limit_id]
        if not _window_valid(bucket.primary, evidence.observed_at_epoch):
            return QuotaDecision("QUOTA_UNKNOWN", "PRIMARY_WINDOW_INVALID", frozenset(), (), True, False)
        if requirement.secondary_required:
            if not _window_valid(bucket.secondary, evidence.observed_at_epoch):
                return QuotaDecision("QUOTA_UNKNOWN", "SECONDARY_WINDOW_REQUIRED", frozenset(), (), True, False)
        elif bucket.secondary is not None and not _window_valid(bucket.secondary, evidence.observed_at_epoch):
            return QuotaDecision("QUOTA_UNKNOWN", "SECONDARY_WINDOW_INVALID", frozenset(), (), True, False)
        if bucket.rate_limit_reached_type is not None:
            if not _text(bucket.rate_limit_reached_type) or bucket.rate_limit_reached_type not in requirement.known_reached_types:
                return QuotaDecision("QUOTA_UNKNOWN", "REACHED_TYPE_UNKNOWN", frozenset(), (), True, False)
            blocking.add(requirement.logical_limit)
        for window in (bucket.primary, bucket.secondary):
            if window is not None and window.used_percent >= 100:
                blocking.add(requirement.logical_limit)
            if window is not None and (window.used_percent >= 100 or bucket.rate_limit_reached_type is not None):
                resets.add(window.resets_at_epoch)
    if blocking:
        state = "LIMIT_REACHED_WEEKLY" if "weekly" in blocking else "LIMIT_REACHED_5H"
        return QuotaDecision(state, "LIMIT_REACHED", frozenset(blocking), tuple(sorted(resets)), True, False)
    return QuotaDecision("AVAILABLE", "CAPACITY_CONFIRMED", frozenset(), (), True, True)


def plan_recheck(decision: object, checkpoint_id: object, now_epoch: object,
                 prior_plan: object = None) -> RecheckPlan | None:
    """Return one idempotent, conceptual read-only check; no timer is started."""
    if (not isinstance(decision, QuotaDecision) or not _text(checkpoint_id) or not _epoch(now_epoch) or
            decision.state not in {"LIMIT_REACHED_5H", "LIMIT_REACHED_WEEKLY"} or
            not decision.relevant_resets_at):
        return None
    future_resets = tuple(value for value in decision.relevant_resets_at if _epoch(value) and value > now_epoch)
    if not future_resets:
        return None
    target = min(future_resets) + RECHECK_DELAY_SECONDS
    key = sha256(f"{checkpoint_id}:{target}:0".encode()).hexdigest()
    if isinstance(prior_plan, RecheckPlan) and prior_plan.checkpoint_id == checkpoint_id and prior_plan.idempotency_key == key:
        return None
    return RecheckPlan(checkpoint_id, 0, target, key, "READ_ONLY_RECHECK_PLANNED")


def backoff_recheck(plan: object, now_epoch: object) -> RecheckPlan | None:
    """Bound failed read-only rechecks; exhausted attempts require manual review."""
    if not isinstance(plan, RecheckPlan) or not _epoch(now_epoch) or plan.attempt < 0 or plan.attempt >= MAX_RECHECK_ATTEMPTS:
        return None
    attempt = plan.attempt + 1
    delay = min(60 * (2 ** (attempt - 1)), MAX_RECHECK_BACKOFF_SECONDS)
    target = now_epoch + delay
    key = sha256(f"{plan.checkpoint_id}:{target}:{attempt}".encode()).hexdigest()
    return RecheckPlan(plan.checkpoint_id, attempt, target, key, "READ_ONLY_RECHECK_BACKOFF")


def checkpoint_for_quota(checkpoint: object, decision: object, now_epoch: object) -> TaskCheckpoint | None:
    """Pause incomplete work without ever treating a checkpoint as authorization."""
    if (not isinstance(checkpoint, TaskCheckpoint) or not isinstance(decision, QuotaDecision) or not _epoch(now_epoch) or
            not _text(checkpoint.checkpoint_id) or not _text(checkpoint.task_id) or
            not isinstance(checkpoint.task_digest_sha256, str) or len(checkpoint.task_digest_sha256) != 64 or
            not _text(checkpoint.provider_id) or not _text(checkpoint.last_confirmed_checkpoint) or
            not isinstance(checkpoint.provider_outcome_may_be_pending, bool) or not _text(checkpoint.review_status) or
            not isinstance(checkpoint.continuation_authorized, bool) or not _text(checkpoint.execution_attempt_id)):
        return None
    if decision.state not in {"LIMIT_REACHED_5H", "LIMIT_REACHED_WEEKLY", "QUOTA_UNKNOWN", "PAUSED", "MANUAL_REVIEW_REQUIRED"}:
        return None
    return replace(checkpoint, execution_status="PAUSED_INCOMPLETE", quota_state=decision.state,
                   evidence_observed_at_epoch=now_epoch, reported_resets_at=decision.relevant_resets_at,
                   continuation_authorized=False)


def assess_resume_candidate(checkpoint: object, decision: object, emergency_stop: object) -> ResumeCandidate:
    """Capacity may yield a candidate, but this function can never authorize execution."""
    if emergency_stop != "false":
        return ResumeCandidate("BLOCKED", "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE", False)
    if not isinstance(checkpoint, TaskCheckpoint) or not isinstance(decision, QuotaDecision):
        return ResumeCandidate("BLOCKED", "CHECKPOINT_OR_QUOTA_INVALID", False)
    if checkpoint.execution_status != "PAUSED_INCOMPLETE" or checkpoint.provider_outcome_may_be_pending:
        return ResumeCandidate("BLOCKED", "INCOMPLETE_OR_PENDING_PROVIDER_OUTCOME", False)
    if decision.state != "AVAILABLE" or not decision.capacity_available or not decision.source_trusted:
        return ResumeCandidate("BLOCKED", "FRESH_CAPACITY_REQUIRED", False)
    return ResumeCandidate("CANDIDATE_REQUIRES_NEW_AUTHORIZATION", "NO_AUTOMATIC_RESUME", False)
