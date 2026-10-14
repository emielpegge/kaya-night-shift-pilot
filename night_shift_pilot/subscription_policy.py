"""Pure, offline subscription-only capacity policy for future manual use.

It deliberately has no provider authentication, quota query, scheduler, retry,
or resume mechanism.  Unknown quota evidence cannot authorize new work.
"""
from __future__ import annotations

from dataclasses import dataclass


SUBSCRIPTION_POLICY_VERSION = "subscription-only-policy-v0.6"
MAXIMUM_QUOTA_EVIDENCE_AGE_SECONDS = 300
EXECUTION_STATES = frozenset({
    "AVAILABLE", "LIMIT_REACHED_5H", "LIMIT_REACHED_WEEKLY", "QUOTA_UNKNOWN",
    "PAUSED", "WAITING_FOR_RESET", "MANUAL_REVIEW_REQUIRED",
})


@dataclass(frozen=True)
class SubscriptionQuotaSnapshot:
    provider_id: str
    policy_version: str
    access_mode: str
    observed_at_epoch: int
    quota_state: str
    reset_at_epoch: int | None
    api_billing_enabled: bool
    extra_credits_allowed: bool
    paid_reset_allowed: bool
    automatic_fallback_enabled: bool
    manual_start_authorized: bool


@dataclass(frozen=True)
class SubscriptionDecision:
    state: str
    next_state: str | None
    code: str


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _epoch(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _false(value: object) -> bool:
    return isinstance(value, bool) and value is False


def _valid(snapshot: object) -> bool:
    return (isinstance(snapshot, SubscriptionQuotaSnapshot) and _text(snapshot.provider_id) and
            snapshot.policy_version == SUBSCRIPTION_POLICY_VERSION and
            snapshot.access_mode == "SUBSCRIPTION_ONLY" and _epoch(snapshot.observed_at_epoch) and
            snapshot.quota_state in {"AVAILABLE", "LIMIT_REACHED_5H", "LIMIT_REACHED_WEEKLY", "QUOTA_UNKNOWN"} and
            (snapshot.reset_at_epoch is None or _epoch(snapshot.reset_at_epoch)) and
            all(isinstance(item, bool) for item in (
                snapshot.api_billing_enabled, snapshot.extra_credits_allowed,
                snapshot.paid_reset_allowed, snapshot.automatic_fallback_enabled,
                snapshot.manual_start_authorized)))


def evaluate_subscription_capacity(snapshot: object, now_epoch: object, *, paused: object = False,
                                   maximum_evidence_age_seconds: object = MAXIMUM_QUOTA_EVIDENCE_AGE_SECONDS) -> SubscriptionDecision:
    """Fail closed: this decision never resumes work or triggers a provider call."""
    if (not _epoch(now_epoch) or not isinstance(paused, bool) or
            not _epoch(maximum_evidence_age_seconds)):
        return SubscriptionDecision("QUOTA_UNKNOWN", "MANUAL_REVIEW_REQUIRED", "CAPACITY_EVIDENCE_INVALID")
    if paused:
        return SubscriptionDecision("PAUSED", None, "MANUAL_PAUSE_ACTIVE")
    if not _valid(snapshot):
        return SubscriptionDecision("QUOTA_UNKNOWN", "MANUAL_REVIEW_REQUIRED", "CAPACITY_EVIDENCE_INVALID")
    if snapshot.observed_at_epoch > now_epoch or now_epoch - snapshot.observed_at_epoch > maximum_evidence_age_seconds:
        return SubscriptionDecision("QUOTA_UNKNOWN", "MANUAL_REVIEW_REQUIRED", "CAPACITY_EVIDENCE_STALE")
    if not all(_false(item) for item in (
        snapshot.api_billing_enabled, snapshot.extra_credits_allowed,
        snapshot.paid_reset_allowed, snapshot.automatic_fallback_enabled)):
        return SubscriptionDecision("MANUAL_REVIEW_REQUIRED", None, "SUBSCRIPTION_ONLY_POLICY_VIOLATION")
    if snapshot.quota_state == "QUOTA_UNKNOWN":
        return SubscriptionDecision("QUOTA_UNKNOWN", "MANUAL_REVIEW_REQUIRED", "QUOTA_NOT_RELIABLY_KNOWN")
    if snapshot.quota_state in {"LIMIT_REACHED_5H", "LIMIT_REACHED_WEEKLY"}:
        if snapshot.reset_at_epoch is None or snapshot.reset_at_epoch <= now_epoch:
            return SubscriptionDecision("MANUAL_REVIEW_REQUIRED", None, "RESET_NOT_RELIABLY_KNOWN")
        return SubscriptionDecision(snapshot.quota_state, "WAITING_FOR_RESET", "NO_NEW_WORK_UNTIL_FRESH_CAPACITY")
    if not snapshot.manual_start_authorized:
        return SubscriptionDecision("MANUAL_REVIEW_REQUIRED", None, "MANUAL_START_AUTHORIZATION_REQUIRED")
    return SubscriptionDecision("AVAILABLE", None, "SUBSCRIPTION_CAPACITY_CONFIRMED")
