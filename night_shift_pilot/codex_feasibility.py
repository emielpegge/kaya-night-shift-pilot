"""Pure offline API-price comparison for the v0.6 non-selected alternative.

This module neither imports an OpenAI SDK nor makes a request.  Its figures are
explicit estimates from a versioned public price input, not billing evidence or
an execution authorization.  Subscription-only policy must not use it to infer
included capacity or operational cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


FEASIBILITY_COST_MODEL_VERSION = "codex-feasibility-cost-v0.6"


@dataclass(frozen=True)
class TokenPrice:
    """USD prices per one million non-cached input/output tokens."""

    model_id: str
    input_per_million_usd: str
    output_per_million_usd: str
    source_verified_on: str


@dataclass(frozen=True)
class TokenScenario:
    name: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class CostEstimate:
    scenario: str
    task_count: int
    input_cost_usd: Decimal
    output_cost_usd: Decimal
    additional_cost_usd: Decimal
    total_cost_usd: Decimal


def _nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _positive_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonnegative_decimal(value: object) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() and parsed >= 0 else None


def validate_price(price: object) -> bool:
    """Validate a static price input before estimating; invalid inputs fail closed."""
    return (isinstance(price, TokenPrice) and _positive_text(price.model_id) and
            _positive_text(price.source_verified_on) and
            _nonnegative_decimal(price.input_per_million_usd) is not None and
            _nonnegative_decimal(price.output_per_million_usd) is not None)


def validate_scenario(scenario: object) -> bool:
    return (isinstance(scenario, TokenScenario) and _positive_text(scenario.name) and
            _nonnegative_int(scenario.input_tokens) and _nonnegative_int(scenario.output_tokens))


def estimate(price: object, scenario: object, task_count: object,
             additional_cost_usd: object = "0") -> CostEstimate | None:
    """Return a deterministic estimate, or None for malformed/non-authoritative inputs."""
    if not validate_price(price) or not validate_scenario(scenario) or not _nonnegative_int(task_count):
        return None
    additional = _nonnegative_decimal(additional_cost_usd)
    if additional is None:
        return None
    input_rate = _nonnegative_decimal(price.input_per_million_usd)
    output_rate = _nonnegative_decimal(price.output_per_million_usd)
    input_cost = (Decimal(scenario.input_tokens) * Decimal(task_count) * input_rate / Decimal(1_000_000))
    output_cost = (Decimal(scenario.output_tokens) * Decimal(task_count) * output_rate / Decimal(1_000_000))
    return CostEstimate(scenario.name, task_count, input_cost, output_cost, additional,
                        input_cost + output_cost + additional)
