# Intelligent Engine Router v0.2: synthetic simulation

This benchmark is offline, deterministic, and synthetic-only. It does not call
providers, access a network, execute models, spend credits, alter router policy,
or modify GitHub workflows. `NIGHT_SHIFT_STOP` remains unchanged because this is
not an execution path.

## Workload and scenarios

`synthetic_workload()` creates exactly 100 fixed tasks using seed `20261014`.
It covers backend, frontend, debugging, research, documentation, architecture,
and review, varying complexity, risk, requirements, quality, budget, and paid
approval. The generated values are neutral fixtures, not production work.

Three scenario fixtures are evaluated:

| ID | Synthetic policy |
| --- | --- |
| A | Equal no-charge mock costs and equal capacity. |
| B | Different synthetic costs; every candidate is a paid mock requiring approval. |
| C | Different synthetic costs, capacities, supported task classes, capabilities, and complexity limits. |

Credits, subscriptions, quotas, and API billing are not converted or compared as
real money. Synthetic USD units only exercise deterministic budget gates.

## Strategies and comparability

- **Intelligent Router**: v0.1 selects the lowest eligible synthetic cost.
- **Fixed Engine**: evaluates only `codex-mock`; it still obeys every router gate.
- **Capability First**: uses the router's eligible set, then selects lowest
  latency rank without cost as its primary tie-breaker.

All strategies receive the same sequential workload and scenario profile copy.
No execution, cost, or capacity is recorded for `NO_EXECUTION`. A fallback is a
selection that differs from the same strategy's capacity-restored preferred
engine. Capacity exhaustion and budget/approval blocks are separately reported,
so missing coverage cannot be presented as savings.

The JSON and Markdown report retain total cost and coverage, but calculate a
cost delta or percentage only on the exact synthetic task IDs handled by both the
strategy and Intelligent Router. A percentage is valid only when that common set
is non-empty and the Intelligent Router's common-task cost is non-zero. A total
cost percentage is valid only with identical handled-task coverage and a non-zero
baseline. Otherwise the report explicitly marks the percentage invalid; a lower
total with fewer handled tasks is not presented as a saving.

Candidate audit records are strategy-consistent: selected candidates carry the
strategy's selection reason, eligible but non-chosen candidates carry an explicit
skip reason, and refused candidates retain their router refusal reasons.

## Run locally

```bash
python3 scripts/run_synthetic_router_simulation.py \
  --output-dir artifacts/router-simulation-v0.2
```

This writes ignored local `report.json` and `report.md` files. The report includes
selected and non-executed counts, engine allocation, fallbacks, capacity events,
budget/approval and quality/risk rejections, total synthetic cost, cost per
handled task, and deltas versus Intelligent Router. Results must not be read as
claims about real provider costs, quality, availability, credits, or savings.
