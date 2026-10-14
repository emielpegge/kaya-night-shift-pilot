"""A fully offline synthetic workflow demonstration for the local store.

Nothing in this module creates a provider client, subprocess, network request,
or live-execution authorization. The active stop is deliberately required.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Final

from .local_execution import (
    LOCAL_EXECUTION_VERSION, LocalExecutionStore, LocalExecutionStoreError,
    PreflightRequest, StoredCheckpoint, StoredSyntheticResult, StoredTask,
    SyntheticTaskArtifact, default_local_store_root, offline_demo_preflight,
)
from .manual_handoff import (
    ALLOWED_REPOSITORY, MANUAL_HANDOFF_VERSION, ManualHandoffError,
    ManualHandoffStore, ManualResult, ManualTaskArtifact,
)


DEMO_TASK_ID: Final = "offline-demo-task-v0.11"
DEMO_REPOSITORY: Final = "example/public-synthetic-pilot"
DEMO_BRANCH: Final = "feature/offline-demo-v0.11"
DEMO_INPUT: Final = "Synthetic fixed task: demonstrate local checkpoint recovery."
DEMO_RESULT: Final = "synthetic_local_workflow_completed"
DEMO_DIRECTORIES: Final = ("night_shift_pilot", "tests")
START_ATTEMPT: Final = "offline-demo-attempt-started"
INTERRUPTED_ATTEMPT: Final = "offline-demo-attempt-interrupted"
RECOVERED_ATTEMPT: Final = "offline-demo-attempt-recovered"
COMPLETED_ATTEMPT: Final = "offline-demo-attempt-completed"
PILOT_REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]


class LocalWorkflowError(ValueError):
    """The strictly synthetic workflow cannot continue safely."""


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _result_digest(task_id: str, attempt_id: str) -> str:
    payload = {
        "schema_version": LOCAL_EXECUTION_VERSION,
        "task_id": task_id,
        "execution_attempt_id": attempt_id,
        "status": "SYNTHETIC_RESULT_READY",
        "synthetic_result": DEMO_RESULT,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def demo_artifact() -> SyntheticTaskArtifact:
    return SyntheticTaskArtifact(
        LOCAL_EXECUTION_VERSION, DEMO_TASK_ID, "synthetic-local-development-task-v1",
        _digest_text(DEMO_INPUT), DEMO_REPOSITORY, DEMO_BRANCH,
    )


def _approved_demo_task() -> StoredTask:
    artifact = demo_artifact()
    artifact_json = asdict(artifact)
    artifact_digest = sha256(
        json.dumps(artifact_json, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return StoredTask(artifact, artifact_digest, "PENDING", "APPROVED", ())


def _preflight_request(task) -> PreflightRequest:
    return PreflightRequest(
        task=task,
        repository=DEMO_REPOSITORY,
        feature_branch=DEMO_BRANCH,
        allowed_directories=("docs", "night_shift_pilot", "tests"),
        requested_directories=DEMO_DIRECTORIES,
        emergency_stop=os.environ.get("NIGHT_SHIFT_STOP"),
        human_authorized=True,
        auth_mode="chatgpt_subscription",
        api_key_mode=False,
        paid_fallback_enabled=False,
        extra_credits_allowed=False,
        paid_reset_allowed=False,
        sandbox_mode="workspace-write",
        automatic_merge=False,
        automatic_deployment=False,
        previous_provider_outcome_uncertain=False,
    )


def _require_demo_preflight(task) -> None:
    decision = offline_demo_preflight(_preflight_request(task))
    if (decision.status, decision.code) != ("ALLOWED", "OFFLINE_DEMO_ONLY"):
        raise LocalWorkflowError(f"OFFLINE_DEMO_PREFLIGHT_{decision.code}")


def _checkpoint(task_id: str, attempt_id: str, status: str) -> StoredCheckpoint:
    return StoredCheckpoint(
        LOCAL_EXECUTION_VERSION, task_id, attempt_id, status, "APPROVED",
        f"{attempt_id}-checkpoint", False,
    )


def start_interrupted_demo(store: LocalExecutionStore):
    """Create the approved synthetic task and intentionally leave it incomplete."""
    expected_task = _approved_demo_task()
    _require_demo_preflight(expected_task)
    task = store.create_task(expected_task.artifact, review_status="APPROVED")
    if task != expected_task:
        raise LocalWorkflowError("SYNTHETIC_DEMO_TASK_MISMATCH")
    running = store.save_checkpoint(_checkpoint(DEMO_TASK_ID, START_ATTEMPT, "RUNNING"))
    paused = store.save_checkpoint(_checkpoint(DEMO_TASK_ID, INTERRUPTED_ATTEMPT, "PAUSED_INCOMPLETE"))
    return paused, {
        "phase": "INTERRUPTED",
        "preflight": "OFFLINE_DEMO_ONLY",
        "task_status": paused.task_status,
        "checkpoint_count": len(paused.execution_attempt_ids),
    }


def recover_demo(store: LocalExecutionStore, task_id: str = DEMO_TASK_ID):
    """Recover only a known paused synthetic demo; uncertain outcomes stay blocked."""
    recovered = {
        task.artifact.task_id: (task, checkpoint)
        for task, checkpoint in store.recover_incomplete()
    }
    task = recovered.get(task_id)
    if task is None:
        raise LocalWorkflowError("NO_INCOMPLETE_SYNTHETIC_DEMO")
    task_record, checkpoint = task
    if (task_record.task_status != "PAUSED_INCOMPLETE" or checkpoint is None or
            checkpoint.provider_outcome_uncertain):
        raise LocalWorkflowError("SYNTHETIC_DEMO_RECOVERY_BLOCKED")
    _require_demo_preflight(task_record)
    running = store.save_checkpoint(_checkpoint(task_id, RECOVERED_ATTEMPT, "RUNNING"))
    result = StoredSyntheticResult(
        LOCAL_EXECUTION_VERSION, task_id, RECOVERED_ATTEMPT, "SYNTHETIC_RESULT_READY",
        DEMO_RESULT, _result_digest(task_id, RECOVERED_ATTEMPT),
    )
    store.save_synthetic_result(result)
    completed = store.save_checkpoint(_checkpoint(task_id, COMPLETED_ATTEMPT, "COMPLETED"))
    return completed, result


def run_demo(store: LocalExecutionStore):
    """Run the complete offline-only path, including a simulated process restart."""
    _, interrupted = start_interrupted_demo(store)
    restarted = LocalExecutionStore(store.root, repository_root=PILOT_REPOSITORY_ROOT)
    completed, result = recover_demo(restarted)
    reviewed = restarted.record_review(completed.artifact.task_id, "APPROVED")
    return {
        "mode": "OFFLINE_SYNTHETIC_DEMO_ONLY",
        "preflight": interrupted["preflight"],
        "task_id": completed.artifact.task_id,
        "task_status": completed.task_status,
        "review_status": reviewed.review_status,
        "review": "SIMULATED_APPROVAL_NOT_HUMAN_DECISION",
        "checkpoint_count": len(completed.execution_attempt_ids),
        "result_sha256": result.result_sha256,
        "live_execution": "NOT_IMPLEMENTED",
    }


def status_payload(store: LocalExecutionStore, task_id: str = DEMO_TASK_ID) -> dict[str, object]:
    task = store.load_task(task_id)
    checkpoints = [asdict(store.load_checkpoint(task_id, attempt_id))
                   for attempt_id in task.execution_attempt_ids]
    try:
        result = asdict(store.load_synthetic_result(task_id))
    except LocalExecutionStoreError as error:
        if str(error) != "STORE_RECORD_MISSING":
            raise
        result = None
    return {"task": asdict(task), "checkpoints": checkpoints, "synthetic_result": result}


def _store_from_args(path: Path | None) -> LocalExecutionStore:
    return LocalExecutionStore(
        path or default_local_store_root(),
        repository_root=PILOT_REPOSITORY_ROOT,
    )


def _manual_store_from_args(path: Path | None) -> ManualHandoffStore:
    return ManualHandoffStore(path or default_local_store_root(), repository_root=PILOT_REPOSITORY_ROOT)


def _manual_result(task, outcome: str, summary: str, tests: str) -> ManualResult:
    payload = {
        "schema_version": MANUAL_HANDOFF_VERSION,
        "task_id": task.artifact.task_id,
        "task_digest_sha256": task.task_digest_sha256,
        "outcome": outcome,
        "summary": summary,
        "tests": tests,
    }
    return ManualResult(**payload, report_digest_sha256=sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest())


def _quick_start(store: ManualHandoffStore, task_id: str, branch: str, scope: str) -> dict[str, object]:
    """Create or safely resume a copy-only manual handoff without invoking Codex."""
    artifact = ManualTaskArtifact(MANUAL_HANDOFF_VERSION, task_id, ALLOWED_REPOSITORY, branch, scope)
    resumed = False
    try:
        store.create_task(artifact)
    except ManualHandoffError as error:
        if str(error) != "DUPLICATE_TASK_ID":
            raise
        task = store.load_task(task_id)
        if task.artifact != artifact:
            raise ManualHandoffError("QUICK_START_TASK_CONFLICT") from None
        resumed = True
    task, prompt = store.handoff(task_id)
    return {
        "mode": "MANUAL_COPY_ONLY",
        "task": asdict(task),
        "codex_prompt": prompt,
        "resumed_existing_task": resumed,
        "next_step": "Copy the handoff to a supervised interactive Codex session; no automatic start occurs.",
    }


def _quick_finish(store: ManualHandoffStore, task_id: str, outcome: str, summary: str, tests: str) -> dict[str, object]:
    """Record a human-supplied report only; review remains a separate human action."""
    task = store.report_result(_manual_result(store.load_task(task_id), outcome, summary, tests))
    result = store.load_result(task_id)
    return {
        "task": asdict(task),
        "result": asdict(result),
        "result_digest_sha256": result.report_digest_sha256,
        "next_step": (
            "Review is blocked for an uncertain outcome."
            if task.task_status == "OUTCOME_UNCERTAIN" else
            "A human must separately run task review with APPROVED or REJECTED."
        ),
    }


def _quick_status(store: ManualHandoffStore, task_id: str) -> dict[str, object]:
    """Present the persistent handoff state without changing it."""
    task = store.load_task(task_id)
    try:
        result = store.load_result(task_id)
    except ManualHandoffError as error:
        if str(error) != "STORE_RECORD_MISSING":
            raise
        result = None
    if task.task_status == "CREATED":
        next_step = "Run quick start again with the same task metadata, or use task handoff."
    elif task.task_status == "HANDOFF_READY":
        next_step = "Complete the supervised manual work, then run quick finish."
    elif task.task_status == "OUTCOME_UNCERTAIN":
        next_step = "Resolve the uncertain outcome manually; review remains blocked."
    elif task.review_status == "NOT_REVIEWED":
        next_step = "A human must separately run task review with APPROVED or REJECTED."
    else:
        next_step = "No further Night Shift action is required."
    return {
        "task_id": task.artifact.task_id,
        "feature_branch": task.artifact.feature_branch,
        "task_status": task.task_status,
        "review_status": task.review_status,
        "result_digest_sha256": result.report_digest_sha256 if result is not None else None,
        "next_step": next_step,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline-only local Night Shift workflow demo")
    parser.add_argument("--store", type=Path, help="absolute local runtime directory outside Git")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--interrupt-only", action="store_true")
    commands.add_parser("status")
    commands.add_parser("recover")
    review = commands.add_parser("review")
    review.add_argument("decision", choices=("APPROVED", "REJECTED"))
    task_command = commands.add_parser("task")
    task_commands = task_command.add_subparsers(dest="task_command", required=True)
    create = task_commands.add_parser("create")
    create.add_argument("--task-id", required=True)
    create.add_argument("--branch", required=True)
    create.add_argument("--scope", required=True)
    show = task_commands.add_parser("show")
    show.add_argument("task_id")
    handoff = task_commands.add_parser("handoff")
    handoff.add_argument("task_id")
    report = task_commands.add_parser("report")
    report.add_argument("task_id")
    report.add_argument("--outcome", choices=("COMPLETED", "UNCERTAIN"), default="COMPLETED")
    report.add_argument("--summary", required=True)
    report.add_argument("--tests", required=True)
    task_review = task_commands.add_parser("review")
    task_review.add_argument("task_id")
    task_review.add_argument("decision", choices=("APPROVED", "REJECTED"))
    quick = commands.add_parser("quick", help="reduce manual handoff administration; remains copy-only")
    quick_commands = quick.add_subparsers(dest="quick_command", required=True)
    quick_start = quick_commands.add_parser("start")
    quick_start.add_argument("--task-id", required=True)
    quick_start.add_argument("--branch", required=True)
    quick_start.add_argument("--scope", required=True)
    quick_finish = quick_commands.add_parser("finish")
    quick_finish.add_argument("task_id")
    quick_finish.add_argument("--outcome", choices=("COMPLETED", "UNCERTAIN"), default="COMPLETED")
    quick_finish.add_argument("--summary", required=True)
    quick_finish.add_argument("--tests", required=True)
    quick_status = quick_commands.add_parser("status")
    quick_status.add_argument("task_id")
    args = parser.parse_args(argv)
    try:
        if args.command == "task":
            store = _manual_store_from_args(args.store)
            if args.task_command == "create":
                task = store.create_task(ManualTaskArtifact(
                    MANUAL_HANDOFF_VERSION, args.task_id, ALLOWED_REPOSITORY, args.branch, args.scope,
                ))
                report = {"task": asdict(task)}
            elif args.task_command == "show":
                report = {"task": asdict(store.load_task(args.task_id))}
            elif args.task_command == "handoff":
                task, prompt = store.handoff(args.task_id)
                report = {"task": asdict(task), "codex_prompt": prompt, "mode": "MANUAL_COPY_ONLY"}
            elif args.task_command == "report":
                task = store.report_result(_manual_result(
                    store.load_task(args.task_id), args.outcome, args.summary, args.tests,
                ))
                report = {"task": asdict(task), "result": asdict(store.load_result(args.task_id))}
            else:
                task = store.review(args.task_id, args.decision)
                report = {"task": asdict(task)}
        elif args.command == "quick":
            store = _manual_store_from_args(args.store)
            if args.quick_command == "start":
                report = _quick_start(store, args.task_id, args.branch, args.scope)
            elif args.quick_command == "finish":
                report = _quick_finish(store, args.task_id, args.outcome, args.summary, args.tests)
            else:
                report = _quick_status(store, args.task_id)
        else:
            store = _store_from_args(args.store)
            if args.command == "demo":
                if args.interrupt_only:
                    _, report = start_interrupted_demo(store)
                else:
                    report = run_demo(store)
            elif args.command == "status":
                report = status_payload(store)
            elif args.command == "recover":
                task, result = recover_demo(store)
                report = {"task_status": task.task_status, "result_sha256": result.result_sha256}
            else:
                task = store.record_review(DEMO_TASK_ID, args.decision)
                report = {"task_id": task.artifact.task_id, "review_status": task.review_status}
        print(json.dumps(report, sort_keys=True))
        return 0
    except (LocalExecutionStoreError, LocalWorkflowError, ManualHandoffError) as error:
        denied = {"status": "DENIED", "code": str(error)}
        if (args.command == "quick" and args.quick_command == "status" and
                str(error) == "STORE_RECORD_MISSING"):
            denied = {
                "status": "DENIED",
                "code": "QUICK_STATUS_TASK_NOT_FOUND",
                "next_step": "Verify the task ID or create the task with quick start.",
            }
        print(json.dumps(denied, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
