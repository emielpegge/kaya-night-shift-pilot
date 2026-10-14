"""A deterministic local MOCK worker. It never invokes an AI service."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .contracts import BoundaryError, SCHEMA_VERSION, digest
from .controller import require_execution_enabled, verify_prepared, write_json


def run(prepared: dict, stop_value: str | None) -> dict:
    require_execution_enabled(stop_value)
    verified = verify_prepared(prepared)
    spec = verified["spec"]
    router = verified["router"]
    result = {
        "schema_version": SCHEMA_VERSION,
        "mode": "MOCK_ONLY",
        "status": "MOCK_SUCCEEDED",
        "task_id": spec["task_id"],
        "run_id": spec["run_id"],
        "spec_sha256": spec["spec_sha256"],
        "router_decision_sha256": router["router_decision_sha256"],
        "selected_engine_id": router["router_decision"]["selected_engine_id"],
        "synthetic_result": "controller_worker_router_handoff_verified",
    }
    result["result_sha256"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(json.loads(args.prepared.read_text()), os.environ.get("NIGHT_SHIFT_STOP"))
        write_json(args.output / "result.json", result)
        print(json.dumps({"status": result["status"], "mode": result["mode"]}))
        return 0
    except BoundaryError as error:
        write_json(args.output / "result.json", {"schema_version": SCHEMA_VERSION, "status": "BLOCKED", "code": str(error)})
        print(json.dumps({"status": "BLOCKED", "code": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
