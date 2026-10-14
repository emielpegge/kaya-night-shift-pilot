"""Fixed-task adapter between the public MOCK controller and the router.

This module contains no provider integration.  It maps the sole pre-approved
synthetic task to an explicit, versioned router specification and validates a
handoff by recomputing the deterministic routing decision.
"""
from __future__ import annotations

from dataclasses import asdict

from .contracts import APPROVED_TASK, BoundaryError, digest
from .router import RoutingDecision, TaskSpec, route, synthetic_profiles


def task_for_approved_spec(spec: object) -> TaskSpec:
    """Map only the fixed public task to explicitly documented router fields."""
    if not isinstance(spec, dict) or spec.get("task_id") != APPROVED_TASK:
        raise BoundaryError("ROUTER_TASK_NOT_APPROVED")
    if spec.get("mode") != "MOCK_ONLY":
        raise BoundaryError("ROUTER_TASK_MODE_INVALID")
    return TaskSpec(
        task_id=APPROVED_TASK,
        kind="documentation",
        complexity=1,
        risk="low",
        required_capabilities=frozenset({"writing"}),
        required_quality="baseline",
        max_synthetic_budget_usd=0,
        paid_call_approved=False,
    )


def decision_payload(decision: RoutingDecision) -> dict:
    """Return the serialisable, auditable subset of a router decision."""
    return {
        "status": decision.status,
        "selected_engine_id": decision.selected_engine_id,
        "rationale": decision.rationale,
        "fallback_engine_ids": list(decision.fallback_engine_ids),
        "candidates": [asdict(candidate) for candidate in decision.candidates],
    }


def routing_handoff(spec: object) -> dict:
    """Build the only allowed router decision for the fixed synthetic task."""
    task = task_for_approved_spec(spec)
    decision = route(task, synthetic_profiles())
    if decision.status != "SELECTED" or not decision.selected_engine_id:
        raise BoundaryError("ROUTER_NO_EXECUTION")
    profiles = {profile.engine_id: profile for profile in synthetic_profiles()}
    profile = profiles.get(decision.selected_engine_id)
    if profile is None:
        raise BoundaryError("ROUTER_ENGINE_UNKNOWN")
    if not profile.mock_only:
        raise BoundaryError("ROUTER_ENGINE_NOT_MOCK_ONLY")
    payload = decision_payload(decision)
    task_payload = {
        "task_id": task.task_id,
        "kind": task.kind,
        "complexity": task.complexity,
        "risk": task.risk,
        "required_capabilities": sorted(task.required_capabilities),
        "required_quality": task.required_quality,
        "max_synthetic_budget_usd": task.max_synthetic_budget_usd,
        "paid_call_approved": task.paid_call_approved,
    }
    return {
        "task_id": spec["task_id"],
        "router_task_sha256": digest(task_payload),
        "router_decision": payload,
        "router_decision_sha256": digest(payload),
    }


def verify_routing_handoff(spec: object, handoff: object) -> dict:
    """Fail closed unless the handoff exactly matches a fresh deterministic run."""
    if not isinstance(handoff, dict):
        raise BoundaryError("ROUTER_HANDOFF_MISSING")
    expected = routing_handoff(spec)
    if handoff.get("task_id") != expected["task_id"]:
        raise BoundaryError("ROUTER_TASK_ID_MISMATCH")
    if handoff.get("router_task_sha256") != expected["router_task_sha256"]:
        raise BoundaryError("ROUTER_TASK_INTEGRITY_FAILED")
    decision = handoff.get("router_decision")
    if not isinstance(decision, dict) or handoff.get("router_decision_sha256") != digest(decision):
        raise BoundaryError("ROUTER_DECISION_INTEGRITY_FAILED")
    if handoff != expected:
        raise BoundaryError("ROUTER_DECISION_MISMATCH")
    return expected
