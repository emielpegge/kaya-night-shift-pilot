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
