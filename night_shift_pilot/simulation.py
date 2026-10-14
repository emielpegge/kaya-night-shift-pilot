"""Reproducible, offline-only benchmark for synthetic router decisions."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from typing import Iterable, Literal

from .router import CandidateDecision, EngineProfile, RoutingDecision, TaskSpec, route, synthetic_profiles


WORKLOAD_SEED = 20261014
TASK_KINDS = ("backend", "frontend", "debugging", "research", "documentation", "architecture", "review")
TASK_CAPABILITIES = {
    "backend": frozenset({"code", "tests"}), "frontend": frozenset({"writing", "reasoning"}),
    "debugging": frozenset({"code", "tests"}), "research": frozenset({"research"}),
    "documentation": frozenset({"writing"}), "architecture": frozenset({"reasoning"}),
    "review": frozenset({"review"}),
}


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    description: str
    profiles: tuple[EngineProfile, ...]


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    selected: int
    no_execution: int
    handled: int
    tasks_per_engine: dict[str, int]
    fallbacks: int
    capacity_exhaustion_events: int
    budget_or_approval_blocked_tasks: int
    candidate_budget_or_approval_rejections: int
    candidate_quality_or_risk_rejections: int
    total_synthetic_cost_usd: int
    synthetic_cost_per_handled_task_usd: float | None
    handled_task_ids: tuple[str, ...]
    synthetic_cost_by_task_id: dict[str, int]


def synthetic_workload() -> tuple[TaskSpec, ...]:
    """Generate exactly 100 stable synthetic tasks without external inputs."""
    # A small arithmetic sequence is used instead of real-world data or random I/O.
    tasks = []
    for index in range(100):
        kind = TASK_KINDS[index % len(TASK_KINDS)]
        tasks.append(TaskSpec(
            task_id=f"synthetic-{WORKLOAD_SEED}-{index + 1:03d}", kind=kind,
            complexity=(index * 7 + WORKLOAD_SEED) % 3 + 1,
            risk=("low", "medium", "high")[(index * 5 + 1) % 3],
            required_capabilities=TASK_CAPABILITIES[kind],
            required_quality=("baseline", "standard", "high")[(index * 11 + 2) % 3],
            max_synthetic_budget_usd=(index * 13 + 1) % 4,
            paid_call_approved=((index * 17 + 3) % 5) < 3,
        ))
    return tuple(tasks)


def _scenario_profiles(costs: dict[str, int], capacities: dict[str, int], billing: str) -> tuple[EngineProfile, ...]:
    profiles = []
    for profile in synthetic_profiles():
        cost = costs[profile.engine_id]
        profiles.append(replace(profile, billing_kind=billing, synthetic_cost_usd=cost,
            capacity_remaining=capacities[profile.engine_id]))
    return tuple(profiles)


def synthetic_scenarios() -> tuple[Scenario, ...]:
    ids = tuple(profile.engine_id for profile in synthetic_profiles())
    scenario_c_profiles = _scenario_profiles(
        {"codex-mock": 2, "claude-mock": 1, "future-provider-mock": 1, "synthetic-paid-mock": 3},
        {"codex-mock": 10, "claude-mock": 12, "future-provider-mock": 6, "synthetic-paid-mock": 4},
        "synthetic_paid_mock")
    scenario_c_profiles = tuple(
        replace(profile, supported_kinds=frozenset({"backend", "debugging", "review"}), max_complexity=2)
        if profile.engine_id == "codex-mock" else
        replace(profile, supported_kinds=frozenset({"research", "documentation", "architecture"}),
            capabilities=frozenset({"writing", "research", "reasoning"}))
        if profile.engine_id == "claude-mock" else
        replace(profile, max_complexity=1)
        if profile.engine_id == "future-provider-mock" else profile
        for profile in scenario_c_profiles)
    return (
        Scenario("A_equal_cost", "All mock profiles have the same documented synthetic cost and capacity.",
            _scenario_profiles(dict.fromkeys(ids, 0), dict.fromkeys(ids, 24), "mock_no_charge")),
        Scenario("B_cost_variance", "Costs vary; all are synthetic paid mocks and require explicit approval.",
            _scenario_profiles({"codex-mock": 2, "claude-mock": 1, "future-provider-mock": 1, "synthetic-paid-mock": 3},
                dict.fromkeys(ids, 24), "synthetic_paid_mock")),
        Scenario("C_cost_capacity_fit", "Costs, capacity, supported work, capabilities, and complexity limits differ across synthetic paid mocks.",
            scenario_c_profiles),
    )


def _eligible_ids(decision: RoutingDecision) -> set[str]:
    eligible_markers = {"LOWEST_ELIGIBLE_SYNTHETIC_COST", "HIGHER_COST_OR_LATENCY"}
    return {candidate.engine_id for candidate in decision.candidates if set(candidate.reasons) <= eligible_markers}


def _choose(strategy: str, task: TaskSpec, profiles: tuple[EngineProfile, ...]) -> RoutingDecision:
    if strategy == "intelligent_router":
        return route(task, profiles)
    if strategy == "fixed_codex_mock":
        fixed = tuple(profile for profile in profiles if profile.engine_id == "codex-mock")
        return route(task, fixed)
    if strategy == "capability_first":
        decision = route(task, profiles)
        eligible = _eligible_ids(decision)
        if not eligible:
            return decision
        profile_by_id = {profile.engine_id: profile for profile in profiles}
        selected = min((profile_by_id[engine_id] for engine_id in eligible),
            key=lambda profile: (profile.latency_rank, profile.engine_id))
        candidates = tuple(
            replace(candidate, outcome="SELECTED", reasons=("CAPABILITY_FIRST_ELIGIBLE",))
            if candidate.engine_id == selected.engine_id else
            replace(candidate, outcome="SKIPPED", reasons=("CAPABILITY_FIRST_ELIGIBLE_NOT_CHOSEN",))
            if candidate.engine_id in eligible else candidate
            for candidate in decision.candidates)
        return RoutingDecision("SELECTED", selected.engine_id, candidates,
            tuple(sorted(eligible - {selected.engine_id})), "CAPABILITY_FIRST_ELIGIBLE_WITH_DETERMINISTIC_TIE_BREAK")
    raise ValueError("STRATEGY_INVALID")


def _has_reason(candidates: Iterable[CandidateDecision], *reasons: str) -> bool:
    return any(set(reasons).intersection(candidate.reasons) for candidate in candidates)


def simulate(scenario: Scenario, strategy: Literal["intelligent_router", "fixed_codex_mock", "capability_first"],
             workload: tuple[TaskSpec, ...] | None = None) -> StrategyResult:
    """Route sequentially, consuming only copied local capacity after selection."""
    workload = synthetic_workload() if workload is None else workload
    current = scenario.profiles
    original = scenario.profiles
    selected = no_execution = fallbacks = capacity_events = budget_blocked = 0
    candidate_budget = candidate_quality_risk = total_cost = 0
    by_engine: Counter[str] = Counter()
    handled_task_ids: list[str] = []
    cost_by_task_id: dict[str, int] = {}
    for task in workload:
        decision = _choose(strategy, task, current)
        candidate_budget += sum(1 for candidate in decision.candidates
            if _has_reason((candidate,), "SYNTHETIC_BUDGET_EXCEEDED", "PAID_CALL_NOT_APPROVED"))
        candidate_quality_risk += sum(1 for candidate in decision.candidates
            if _has_reason((candidate,), "QUALITY_REQUIREMENT_UNMET", "FEEDBACK_QUALITY_UNMET", "RISK_EXCEEDED"))
        capacity_events += int(_has_reason(decision.candidates, "CAPACITY_UNAVAILABLE"))
        if decision.status != "SELECTED" or not decision.selected_engine_id:
            no_execution += 1
            budget_blocked += int(_has_reason(decision.candidates, "SYNTHETIC_BUDGET_EXCEEDED", "PAID_CALL_NOT_APPROVED"))
            continue
        baseline = _choose(strategy, task, original)
        fallbacks += int(baseline.selected_engine_id is not None and baseline.selected_engine_id != decision.selected_engine_id)
        selected += 1
        handled_task_ids.append(task.task_id)
        by_engine[decision.selected_engine_id] += 1
        selected_profile = next(profile for profile in current if profile.engine_id == decision.selected_engine_id)
        task_cost = selected_profile.synthetic_cost_usd or 0
        total_cost += task_cost
        cost_by_task_id[task.task_id] = task_cost
        current = tuple(replace(profile, capacity_remaining=profile.capacity_remaining - 1)
            if profile.engine_id == decision.selected_engine_id else profile for profile in current)
    return StrategyResult(strategy, selected, no_execution, selected, dict(sorted(by_engine.items())), fallbacks,
        capacity_events, budget_blocked, candidate_budget, candidate_quality_risk, total_cost,
        round(total_cost / selected, 4) if selected else None, tuple(handled_task_ids), dict(sorted(cost_by_task_id.items())))


def comparable_costs(result: StrategyResult, intelligent: StrategyResult) -> dict:
    """Compare costs only on task IDs both strategies actually handled."""
    common_ids = tuple(sorted(set(result.handled_task_ids).intersection(intelligent.handled_task_ids)))
    result_common_cost = sum(result.synthetic_cost_by_task_id[task_id] for task_id in common_ids)
    intelligent_common_cost = sum(intelligent.synthetic_cost_by_task_id[task_id] for task_id in common_ids)
    same_coverage = set(result.handled_task_ids) == set(intelligent.handled_task_ids)
    percent_valid = bool(common_ids) and intelligent_common_cost > 0
    return {
        "common_handled_task_count": len(common_ids),
        "result_cost_on_common_handled_tasks_usd": result_common_cost,
        "intelligent_cost_on_common_handled_tasks_usd": intelligent_common_cost,
        "common_task_cost_delta_vs_intelligent_usd": result_common_cost - intelligent_common_cost,
        "common_task_cost_percent_delta_vs_intelligent": round(
            (result_common_cost - intelligent_common_cost) / intelligent_common_cost * 100, 4) if percent_valid else None,
        "common_task_percent_comparison_valid": percent_valid,
        "common_task_percent_comparison_reason": "VALID_SAME_TASK_IDS_NONZERO_BASELINE_COST" if percent_valid
            else "NOT_VALID_NO_COMMON_TASKS_OR_ZERO_BASELINE_COST",
        "full_coverage_cost_comparison_valid": same_coverage and intelligent.total_synthetic_cost_usd > 0,
        "full_coverage_cost_comparison_reason": "VALID_IDENTICAL_COVERAGE_NONZERO_BASELINE_COST"
            if same_coverage and intelligent.total_synthetic_cost_usd > 0
            else "NOT_VALID_DIFFERENT_COVERAGE_OR_ZERO_BASELINE_COST",
    }


def benchmark() -> dict:
    """Return a JSON-serialisable comparison; outputs are synthetic, not financial claims."""
    workload = synthetic_workload()
    report = {"schema_version": "router-simulation-v0.2", "seed": WORKLOAD_SEED,
        "workload_size": len(workload), "workload_by_kind": dict(sorted(Counter(task.kind for task in workload).items())),
        "scenarios": []}
    for scenario in synthetic_scenarios():
        results = [simulate(scenario, strategy, workload) for strategy in
            ("intelligent_router", "fixed_codex_mock", "capability_first")]
        baseline = results[0]
        report["scenarios"].append({"scenario_id": scenario.scenario_id, "description": scenario.description,
            "profiles": [asdict(profile) | {"supported_kinds": sorted(profile.supported_kinds), "capabilities": sorted(profile.capabilities)} for profile in scenario.profiles],
            "results": [asdict(result) | {"difference_vs_intelligent": {
                "handled": result.handled - baseline.handled,
                "total_synthetic_cost_usd": result.total_synthetic_cost_usd - baseline.total_synthetic_cost_usd,
            }, "comparable_costs_vs_intelligent": comparable_costs(result, baseline)} for result in results]})
    return report


def markdown_report(report: dict) -> str:
    lines = ["# Synthetic Intelligent Engine Router benchmark", "",
        f"Seed: `{report['seed']}` · workload: **{report['workload_size']}** synthetic tasks.", "",
        "All costs, capacities, profiles, and results below are synthetic fixtures. They do not represent provider pricing, credits, subscriptions, model quality, or savings.", ""]
    for scenario in report["scenarios"]:
        lines += [f"## {scenario['scenario_id']}", "", scenario["description"], "",
            "| Strategy | Selected / NO_EXECUTION | Handled | Total cost | Cost / handled | Common tasks | Cost on common tasks | Common % valid? | Fallbacks | Capacity events | Budget-blocked tasks |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |"]
        for result in scenario["results"]:
            cost_per = "n/a" if result["synthetic_cost_per_handled_task_usd"] is None else f"{result['synthetic_cost_per_handled_task_usd']:.4f}"
            comparison = result["comparable_costs_vs_intelligent"]
            percent = "n/a" if comparison["common_task_cost_percent_delta_vs_intelligent"] is None else f"{comparison['common_task_cost_percent_delta_vs_intelligent']:.4f}%"
            lines.append(f"| {result['strategy']} | {result['selected']} / {result['no_execution']} | {result['handled']} | {result['total_synthetic_cost_usd']} | {cost_per} | {comparison['common_handled_task_count']} | {comparison['result_cost_on_common_handled_tasks_usd']} | {percent} ({comparison['common_task_percent_comparison_reason']}) | {result['fallbacks']} | {result['capacity_exhaustion_events']} | {result['budget_or_approval_blocked_tasks']} |")
        lines.append("")
    return "\n".join(lines) + "\n"
