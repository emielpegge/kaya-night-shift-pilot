"""Small, serialisable contracts shared by the controller and mock worker."""
from __future__ import annotations

from hashlib import sha256
import json

APPROVED_TASK = "synthetic-documentation-check-v1"
SCHEMA_VERSION = "night-shift-public-mock-v1"


class BoundaryError(ValueError):
    """A safety boundary stopped the pilot before any worker work occurred."""


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def approved_spec(run_id: str) -> dict[str, str]:
    """Return the sole fixed, data-independent mock task."""
    if not run_id or len(run_id) > 128:
        raise BoundaryError("RUN_ID_INVALID")
    spec = {
        "schema_version": SCHEMA_VERSION,
        "mode": "MOCK_ONLY",
        "task_id": APPROVED_TASK,
        "run_id": run_id,
        "input": "Synthetic fixed task: verify the controller-to-worker handoff.",
    }
    spec["spec_sha256"] = digest(spec)
    return spec
