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


def route(task: TaskSpec, engines: Iterable[EngineProfile], feedback: Iterable[FeedbackRecord] = ()) -> RoutingDecision:
    """Choose the least-cost eligible MOCK engine with deterministic tie breaks."""
    if task.complexity not in {1, 2, 3} or task.max_synthetic_budget_usd < 0:
        return RoutingDecision("NO_EXECUTION", None, (), (), "TASK_POLICY_INVALID")
    feedback = tuple(feedback)
    evaluated = [(engine, refusal_reasons(task, engine, feedback)) for engine in engines]
    eligible = sorted((engine for engine, reasons in evaluated if not reasons),
        key=lambda engine: (engine.synthetic_cost_usd, engine.latency_rank, engine.engine_id))
    selected = eligible[0] if eligible else None
    candidates = tuple(CandidateDecision(
        engine.engine_id,
        "SELECTED" if selected and engine.engine_id == selected.engine_id else "SKIPPED",
        ("LOWEST_ELIGIBLE_SYNTHETIC_COST",) if selected and engine.engine_id == selected.engine_id else reasons or ("HIGHER_COST_OR_LATENCY",),
        engine.synthetic_cost_usd, engine.capacity_remaining,
    ) for engine, reasons in evaluated)
    if selected is None:
        return RoutingDecision("NO_EXECUTION", None, candidates, (), "NO_SAFE_AFFORDABLE_MOCK_ENGINE")
    return RoutingDecision("SELECTED", selected.engine_id, candidates,
        tuple(engine.engine_id for engine in eligible[1:]),
        "LOWEST_ELIGIBLE_SYNTHETIC_COST_WITH_DETERMINISTIC_TIE_BREAK")
