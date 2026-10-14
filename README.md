# Public Night Shift MOCK pilot

An isolated, public GitHub Actions safety pilot. It uses generic code and one
fixed synthetic task only. See [the acceptance guide](docs/ACCEPTANCE_GUIDE.md).

The workflow is manual-only, read-only, and cannot publish code or call a model.
It is deliberately **not** a production automation system.

The [Intelligent Engine Router v0.1](docs/INTELLIGENT_ENGINE_ROUTER_V0_1.md) is
a separate deterministic synthetic decision component with no workflow or
provider integration.

The [v0.2 simulation](docs/INTELLIGENT_ENGINE_ROUTER_V0_2_SIMULATION.md) compares
synthetic routing strategies locally and writes only ignored local reports.

The [v0.3 router integration](docs/NIGHT_SHIFT_ROUTER_INTEGRATION_V0_3.md)
connects that deterministic router to the existing controller and worker while
remaining mock-only, manual-only, and fail-closed.

The [v0.4 provider architecture](docs/REAL_AI_PROVIDER_ARCHITECTURE_V0_4.md)
defines inert, versioned future-provider contracts. It does not implement a
provider connection or enable live execution.

The [v0.5 Codex-first design](docs/CODEX_FIRST_EXECUTION_ARCHITECTURE_V0_5.md)
adds only inert private-boundary, grant and accounting design contracts; every
live request remains denied.

The [v0.6 feasibility record](docs/CODEX_V0_6_GO_NO_GO.md) is now
subscription-only: it records a manual, quota-gated design and explicit NO-GO
for unmanaged execution. It does not add a provider connection or change the
live denial.

The [v0.7 quota-monitor design](docs/QUOTA_MONITOR_GO_NO_GO_V0_7.md) adds only
offline App Server quota normalization, conceptual recheck planning and
checkpoint contracts. It remains NO-GO for a live connector and cannot start
or resume AI work.

The [v0.8 subscription-integration feasibility record](docs/SUBSCRIPTION_INTEGRATION_GO_NO_GO_V0_8.md)
compares current official local and hosted routes, documents the zero-additional-
cost boundary, and remains NO-GO for live Night Shift subscription integration.

The [v0.9 local-subscription feasibility record](docs/LOCAL_SUBSCRIPTION_GO_NO_GO_V0_9.md)
separates documented local Codex capabilities from KAYA's authorization and
zero-cost requirements. It permits no live integration and remains NO-GO for
unattended execution.

The [v0.10 local execution foundation](docs/LOCAL_EXECUTION_FOUNDATION_V0_10.md)
adds persistent synthetic task/checkpoint state and an offline preflight only;
it cannot invoke Codex or authorize a provider start.

The v0.11 offline demo can be run in an empty local runtime directory with
`NIGHT_SHIFT_STOP=true python3 -m night_shift_pilot.local_workflow --store /absolute/runtime demo`.
It requires that exact active stop value and records only a synthetic result.
Its approval is explicitly simulated, not a human decision; use `review` to
record a local human approval or rejection.

For a supervised, copy-only task handoff use `task create`, `task handoff`,
`task report`, and `task review` through the same CLI. It stores only local
metadata and cannot start Codex.
