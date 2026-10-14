"""Deterministic, synthetic-only engine routing for the public MOCK pilot.

Profiles are policy fixtures, not claims about real providers, subscriptions,
credits, model quality, availability, or prices. This module never calls an
engine or provider; it produces an auditable decision only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Literal


TaskKind = Literal["backend", "frontend", "debugging", "research", "documentation", "architecture", "review"]
QualityLevel = Literal["baseline", "standard", "high"]
RiskLevel = Literal["low", "medium", "high"]

QUALITY_RANK = {"baseline": 1, "standard": 2, "high": 3}
RISK_RANK = {"low": 1, "medium": 2, "high": 3}
TASK_KINDS = frozenset({"backend", "frontend", "debugging", "research", "documentation", "architecture", "review"})
BILLING_KINDS = frozenset({"mock_no_charge", "synthetic_paid_mock", "unknown"})


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    kind: TaskKind
    complexity: int
    risk: RiskLevel
    required_capabilities: FrozenSet[str]
    required_quality: QualityLevel
    max_synthetic_budget_usd: int
    paid_call_approved: bool = False


@dataclass(frozen=True)
class EngineProfile:
    engine_id: str
    provider: str
    mock_only: bool
    enabled: bool
    supported_kinds: FrozenSet[TaskKind]
    capabilities: FrozenSet[str]
    max_complexity: int
    max_risk: RiskLevel
    quality: QualityLevel
    latency_rank: int
    billing_kind: Literal["mock_no_charge", "synthetic_paid_mock", "unknown"]
    synthetic_cost_usd: int | None
    capacity_remaining: int


@dataclass(frozen=True)
class FeedbackRecord:
    engine_id: str
    quality_score: int
    reliability_score: int


@dataclass(frozen=True)
class CandidateDecision:
    engine_id: str
    outcome: Literal["SELECTED", "SKIPPED"]
    reasons: tuple[str, ...]
    synthetic_cost_usd: int | None
    capacity_remaining: int


@dataclass(frozen=True)
class RoutingDecision:
    status: Literal["SELECTED", "NO_EXECUTION"]
    selected_engine_id: str | None
    candidates: tuple[CandidateDecision, ...]
    fallback_engine_ids: tuple[str, ...]
    rationale: str


def synthetic_profiles() -> tuple[EngineProfile, ...]:
    """Fixed profiles solely for unit tests and a public demonstration."""
    return (
        EngineProfile("codex-mock", "codex", True, True,
            frozenset({"backend", "debugging", "architecture", "review"}),
            frozenset({"code", "tests", "reasoning", "review"}), 3, "high", "high", 2,
            "mock_no_charge", 0, 5),
        EngineProfile("claude-mock", "claude", True, True,
            frozenset({"frontend", "research", "documentation", "architecture", "review"}),
            frozenset({"writing", "reasoning", "review", "research"}), 3, "high", "high", 1,
            "mock_no_charge", 0, 4),
        EngineProfile("future-provider-mock", "future-provider", True, True,
            frozenset({"documentation", "research", "review"}),
            frozenset({"writing", "research", "review"}), 2, "medium", "standard", 1,
            "mock_no_charge", 0, 3),
        EngineProfile("synthetic-paid-mock", "synthetic-provider", True, True,
            frozenset({"backend"}), frozenset({"code", "tests"}), 3, "high", "high", 1,
            "synthetic_paid_mock", 1, 2),
    )


def is_non_boolean_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def valid_string_set(value: object) -> bool:
    return isinstance(value, frozenset) and all(isinstance(item, str) and item for item in value)


def valid_choice(value: object, allowed: frozenset[str] | dict[str, int]) -> bool:
    """Membership is safe only after rejecting non-string/unhashable values."""
    return isinstance(value, str) and value in allowed


def validate_task(task: object) -> tuple[str, ...]:
    reasons: list[str] = []
    if not isinstance(getattr(task, "task_id", None), str) or not getattr(task, "task_id", ""):
        reasons.append("TASK_ID_INVALID")
    if not valid_choice(getattr(task, "kind", None), TASK_KINDS):
        reasons.append("TASK_KIND_INVALID")
    if not is_non_boolean_int(getattr(task, "complexity", None)) or getattr(task, "complexity", 0) not in {1, 2, 3}:
        reasons.append("TASK_COMPLEXITY_INVALID")
    if not valid_choice(getattr(task, "risk", None), RISK_RANK):
        reasons.append("TASK_RISK_INVALID")
    if not valid_string_set(getattr(task, "required_capabilities", None)):
        reasons.append("TASK_CAPABILITIES_INVALID")
    if not valid_choice(getattr(task, "required_quality", None), QUALITY_RANK):
        reasons.append("TASK_QUALITY_INVALID")
    budget = getattr(task, "max_synthetic_budget_usd", None)
    if not is_non_boolean_int(budget) or budget < 0:
        reasons.append("TASK_BUDGET_INVALID")
    if not isinstance(getattr(task, "paid_call_approved", None), bool):
        reasons.append("TASK_PAID_APPROVAL_INVALID")
    return tuple(reasons)


def validate_engine(engine: object) -> tuple[str, ...]:
    reasons: list[str] = []
    if not isinstance(getattr(engine, "engine_id", None), str) or not getattr(engine, "engine_id", ""):
        reasons.append("ENGINE_ID_INVALID")
    if not isinstance(getattr(engine, "provider", None), str) or not getattr(engine, "provider", ""):
        reasons.append("PROVIDER_INVALID")
    if not isinstance(getattr(engine, "mock_only", None), bool):
        reasons.append("MOCK_ONLY_INVALID")
    if not isinstance(getattr(engine, "enabled", None), bool):
        reasons.append("ENABLED_INVALID")
    supported = getattr(engine, "supported_kinds", None)
    if not valid_string_set(supported) or not supported.issubset(TASK_KINDS):
        reasons.append("SUPPORTED_TASK_KINDS_INVALID")
    if not valid_string_set(getattr(engine, "capabilities", None)):
        reasons.append("ENGINE_CAPABILITIES_INVALID")
    maximum = getattr(engine, "max_complexity", None)
    if not is_non_boolean_int(maximum) or maximum not in {1, 2, 3}:
        reasons.append("ENGINE_COMPLEXITY_INVALID")
    if not valid_choice(getattr(engine, "max_risk", None), RISK_RANK):
        reasons.append("ENGINE_RISK_INVALID")
    if not valid_choice(getattr(engine, "quality", None), QUALITY_RANK):
        reasons.append("ENGINE_QUALITY_INVALID")
    latency = getattr(engine, "latency_rank", None)
    if not is_non_boolean_int(latency) or latency < 1:
        reasons.append("LATENCY_RANK_INVALID")
    billing = getattr(engine, "billing_kind", None)
    cost = getattr(engine, "synthetic_cost_usd", None)
    if not valid_choice(billing, BILLING_KINDS):
        reasons.append("BILLING_KIND_INVALID")
    elif billing == "unknown":
        if cost is not None:
            reasons.append("UNKNOWN_BILLING_COST_INVALID")
    elif not is_non_boolean_int(cost) or cost < 0:
        reasons.append("SYNTHETIC_COST_INVALID")
    elif billing == "mock_no_charge" and cost != 0:
        reasons.append("MOCK_COST_INVALID")
    capacity = getattr(engine, "capacity_remaining", None)
    if not is_non_boolean_int(capacity) or capacity < 0:
        reasons.append("CAPACITY_INVALID")
    return tuple(reasons)


def validate_feedback(records: Iterable[object]) -> tuple[str, ...]:
    reasons = []
    for record in records:
        if (not isinstance(getattr(record, "engine_id", None), str) or
                not is_non_boolean_int(getattr(record, "quality_score", None)) or
                not is_non_boolean_int(getattr(record, "reliability_score", None)) or
                not 1 <= getattr(record, "quality_score", 0) <= 5 or
                not 1 <= getattr(record, "reliability_score", 0) <= 5):
            reasons.append("FEEDBACK_RECORD_INVALID")
            break
    return tuple(reasons)


def feedback_quality(engine_id: str, records: Iterable[FeedbackRecord]) -> QualityLevel | None:
    scores = [min(record.quality_score, record.reliability_score) for record in records if record.engine_id == engine_id]
    if not scores:
        return None
    average = sum(scores) / len(scores)
    return "high" if average >= 4.5 else "standard" if average >= 3 else "baseline"


def refusal_reasons(task: TaskSpec, engine: EngineProfile, feedback: Iterable[FeedbackRecord]) -> tuple[str, ...]:
    reasons: list[str] = []
    if not engine.mock_only:
        reasons.append("NOT_MOCK_ONLY")
    if not engine.enabled:
        reasons.append("ENGINE_DISABLED")
    if task.kind not in engine.supported_kinds:
        reasons.append("TASK_KIND_UNSUPPORTED")
    if not task.required_capabilities.issubset(engine.capabilities):
        reasons.append("REQUIRED_CAPABILITY_MISSING")
    if task.complexity > engine.max_complexity:
        reasons.append("COMPLEXITY_EXCEEDED")
    if RISK_RANK[task.risk] > RISK_RANK[engine.max_risk]:
        reasons.append("RISK_EXCEEDED")
    if QUALITY_RANK[engine.quality] < QUALITY_RANK[task.required_quality]:
        reasons.append("QUALITY_REQUIREMENT_UNMET")
    observed_quality = feedback_quality(engine.engine_id, feedback)
    if observed_quality is not None and QUALITY_RANK[observed_quality] < QUALITY_RANK[task.required_quality]:
        reasons.append("FEEDBACK_QUALITY_UNMET")
    if engine.capacity_remaining < 1:
        reasons.append("CAPACITY_UNAVAILABLE")
    if engine.synthetic_cost_usd is None or engine.billing_kind == "unknown":
        reasons.append("COST_NOT_VERIFIABLE")
    else:
        if engine.synthetic_cost_usd > task.max_synthetic_budget_usd:
            reasons.append("SYNTHETIC_BUDGET_EXCEEDED")
        if engine.synthetic_cost_usd > 0 and not task.paid_call_approved:
            reasons.append("PAID_CALL_NOT_APPROVED")
    return tuple(reasons)


def audit_engine_id(engine: object, index: int) -> str:
    engine_id = getattr(engine, "engine_id", None)
    return engine_id if isinstance(engine_id, str) and engine_id else "invalid-engine-id"


def audit_cost(engine: object) -> int | None:
    cost = getattr(engine, "synthetic_cost_usd", None)
    return cost if is_non_boolean_int(cost) and cost >= 0 else None


def audit_capacity(engine: object) -> int:
    capacity = getattr(engine, "capacity_remaining", None)
    return capacity if is_non_boolean_int(capacity) and capacity >= 0 else -1


def route(task: TaskSpec, engines: Iterable[EngineProfile], feedback: Iterable[FeedbackRecord] = ()) -> RoutingDecision:
    """Choose the least-cost eligible MOCK engine with deterministic tie breaks."""
    task_reasons = validate_task(task)
    feedback = tuple(feedback)
    feedback_reasons = validate_feedback(feedback)
    indexed = tuple(enumerate(tuple(engines)))
    duplicate_ids = {engine_id for engine_id in (audit_engine_id(engine, index) for index, engine in indexed)
        if sum(audit_engine_id(other, other_index) == engine_id for other_index, other in indexed) > 1}
    if task_reasons or feedback_reasons:
        rationale = "TASK_POLICY_INVALID" if task_reasons else "FEEDBACK_POLICY_INVALID"
        return RoutingDecision("NO_EXECUTION", None, (), (), rationale + ":" + ",".join(task_reasons + feedback_reasons))
    evaluated = []
    for index, engine in indexed:
        reasons = list(validate_engine(engine))
        engine_id = audit_engine_id(engine, index)
        if engine_id in duplicate_ids:
            reasons.append("DUPLICATE_ENGINE_ID")
        if not reasons:
            reasons.extend(refusal_reasons(task, engine, feedback))
        evaluated.append((engine_id, engine, tuple(reasons)))
    evaluated.sort(key=lambda item: (item[0], item[2]))
    eligible = sorted((engine for _, engine, reasons in evaluated if not reasons),
        key=lambda engine: (engine.synthetic_cost_usd, engine.latency_rank, engine.engine_id))
    selected = eligible[0] if eligible else None
    candidates = tuple(CandidateDecision(
        engine_id,
        "SELECTED" if selected and engine_id == selected.engine_id else "SKIPPED",
        ("LOWEST_ELIGIBLE_SYNTHETIC_COST",) if selected and engine_id == selected.engine_id else reasons or ("HIGHER_COST_OR_LATENCY",),
        audit_cost(engine), audit_capacity(engine),
    ) for engine_id, engine, reasons in evaluated)
    if selected is None:
        return RoutingDecision("NO_EXECUTION", None, candidates, (), "NO_SAFE_AFFORDABLE_MOCK_ENGINE")
    return RoutingDecision("SELECTED", selected.engine_id, candidates,
        tuple(engine.engine_id for engine in eligible[1:]),
        "LOWEST_ELIGIBLE_SYNTHETIC_COST_WITH_DETERMINISTIC_TIE_BREAK")
