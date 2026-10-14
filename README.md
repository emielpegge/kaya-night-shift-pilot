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
