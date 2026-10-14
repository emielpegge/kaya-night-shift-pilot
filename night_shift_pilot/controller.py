"""Fail-closed controller for the public, data-independent MOCK pilot.

This module deliberately has no GitHub write transport, shell execution, model
client, network client other than one anonymous public branch-metadata read, or
access to external data. It only writes local JSON files for workflow artifacts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from .contracts import APPROVED_TASK, BoundaryError, SCHEMA_VERSION, approved_spec, digest
from .router_adapter import routing_handoff, verify_routing_handoff


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execution_enabled(value: str | None) -> bool:
    """Allow execution only for the exact explicit repository-variable value."""
    return value == "false"


def require_execution_enabled(value: str | None) -> None:
    if not execution_enabled(value):
        raise BoundaryError("NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")


def public_branch_protected(repository: str, branch: str, opener=urlopen) -> bool:
    """Read only public branch metadata and accept only an explicit true value."""
    if not repository or "/" not in repository or branch != "main":
        raise BoundaryError("REPOSITORY_OR_BRANCH_INVALID")
    request = Request(
        f"https://api.github.com/repos/{repository}/branches/{branch}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "night-shift-public-mock"},
    )
    try:
        with opener(request, timeout=10) as response:
            payload = json.loads(response.read(65536))
    except (URLError, OSError, json.JSONDecodeError):
        raise BoundaryError("BRANCH_PROTECTION_UNREADABLE") from None
    if payload.get("protected") is not True:
        raise BoundaryError("MAIN_NOT_PROTECTED")
    return True


def verify_environment(environment: dict[str, str], branch_check=public_branch_protected) -> None:
    if environment.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise BoundaryError("MANUAL_DISPATCH_REQUIRED")
    if environment.get("GITHUB_REF") != "refs/heads/main":
        raise BoundaryError("MAIN_REF_REQUIRED")
    require_execution_enabled(environment.get("NIGHT_SHIFT_STOP"))
    if environment.get("APPROVED_TASK") != APPROVED_TASK:
        raise BoundaryError("TASK_NOT_PREAPPROVED")
    branch_check(environment.get("GITHUB_REPOSITORY", ""), "main")


def prepare(environment: dict[str, str], branch_check=public_branch_protected) -> dict:
    verify_environment(environment, branch_check)
    spec = approved_spec(environment.get("GITHUB_RUN_ID", ""))
    router = routing_handoff(spec)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "PREPARED",
        "status": "READY_FOR_MOCK_WORKER",
        "at": utc_now(),
        "spec": spec,
        "spec_sha256": spec["spec_sha256"],
        "router": router,
        "report_sha256": digest({
            "phase": "PREPARED", "spec_sha256": spec["spec_sha256"],
            "router_decision_sha256": router["router_decision_sha256"],
        }),
    }


def verify_prepared(prepared: object) -> dict:
    """Validate all controller-to-worker bindings before mock processing."""
    if not isinstance(prepared, dict):
        raise BoundaryError("PREPARED_HANDOFF_MISSING")
    if (prepared.get("schema_version") != SCHEMA_VERSION or prepared.get("phase") != "PREPARED" or
            prepared.get("status") != "READY_FOR_MOCK_WORKER"):
        raise BoundaryError("PREPARED_HANDOFF_CONTRACT_INVALID")
    spec = prepared.get("spec")
    canonical_spec = {k: v for k, v in spec.items() if k != "spec_sha256"} if isinstance(spec, dict) else None
    if not isinstance(spec, dict) or spec.get("spec_sha256") != digest(canonical_spec):
        raise BoundaryError("SPEC_INTEGRITY_FAILED")
    if prepared.get("spec_sha256") != spec["spec_sha256"]:
        raise BoundaryError("PREPARED_SPEC_MISMATCH")
    router = verify_routing_handoff(spec, prepared.get("router"))
    expected_report_digest = digest({
        "phase": "PREPARED", "spec_sha256": spec["spec_sha256"],
        "router_decision_sha256": router["router_decision_sha256"],
    })
    if prepared.get("report_sha256") != expected_report_digest:
        raise BoundaryError("PREPARED_HANDOFF_INTEGRITY_FAILED")
    return {"spec": spec, "router": router}


def finalize(prepared: dict, result: dict, environment: dict[str, str]) -> dict:
    require_execution_enabled(environment.get("NIGHT_SHIFT_STOP"))
    verified = verify_prepared(prepared)
    spec = verified["spec"]
    router = verified["router"]
    if not isinstance(result, dict):
        raise BoundaryError("WORKER_RESULT_INVALID")
    if result.get("spec_sha256") != spec["spec_sha256"]:
        raise BoundaryError("WORKER_RESULT_MISMATCH")
    if (result.get("task_id") != spec["task_id"] or result.get("run_id") != spec["run_id"] or
            result.get("router_decision_sha256") != router["router_decision_sha256"] or
            result.get("selected_engine_id") != router["router_decision"]["selected_engine_id"]):
        raise BoundaryError("WORKER_ROUTER_RESULT_MISMATCH")
    canonical_result = {key: value for key, value in result.items() if key != "result_sha256"} if isinstance(result, dict) else None
    if not isinstance(result, dict) or result.get("result_sha256") != digest(canonical_result):
        raise BoundaryError("WORKER_RESULT_INTEGRITY_FAILED")
    if (result.get("schema_version") != SCHEMA_VERSION or result.get("status") != "MOCK_SUCCEEDED" or result.get("mode") != "MOCK_ONLY" or
            result.get("synthetic_result") != "controller_worker_router_handoff_verified"):
        raise BoundaryError("WORKER_RESULT_INVALID")
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": "FINALIZED",
        "status": "MOCK_COMPLETED_NO_PUBLICATION",
        "at": utc_now(),
        "task_id": spec["task_id"],
        "run_id": spec["run_id"],
        "spec_sha256": spec["spec_sha256"],
        "router_decision_sha256": router["router_decision_sha256"],
        "selected_engine_id": router["router_decision"]["selected_engine_id"],
        "worker_result_sha256": digest(result),
        "guarantees": [
            "synthetic_input_only",
            "no_model_or_paid_api_call",
            "no_git_write_or_pull_request",
            "no_deployment_or_schedule",
        ],
    }
    report["report_sha256"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("prepare", "finalize"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    try:
        if args.role == "prepare":
            report = prepare(dict(os.environ))
            write_json(args.output / "prepared.json", report)
        else:
            if not args.prepared or not args.result:
                raise BoundaryError("FINALIZE_INPUTS_REQUIRED")
            report = finalize(json.loads(args.prepared.read_text()), json.loads(args.result.read_text()), dict(os.environ))
            write_json(args.output / "report.json", report)
        print(json.dumps({"status": report["status"], "phase": report["phase"]}))
        return 0
    except BoundaryError as error:
        report = {"schema_version": SCHEMA_VERSION, "phase": args.role.upper(), "status": "BLOCKED", "code": str(error), "at": utc_now()}
        write_json(args.output / "report.json", report)
        print(json.dumps(report))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
