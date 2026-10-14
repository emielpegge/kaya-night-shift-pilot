"""Persistent, administrative-only handoff records for supervised Codex work.

This module cannot start Codex, a subprocess, a network request, or a provider.
It writes only local metadata supplied by a human operator.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Final


MANUAL_HANDOFF_VERSION: Final = "manual-codex-handoff-v0.12"
ALLOWED_REPOSITORY: Final = "emielpegge/kaya-night-shift-pilot"
TASK_STATUSES: Final = frozenset({"CREATED", "HANDOFF_READY", "RESULT_REPORTED", "OUTCOME_UNCERTAIN"})
REVIEW_STATUSES: Final = frozenset({"NOT_REVIEWED", "APPROVED", "REJECTED"})
FORBIDDEN_METADATA_MARKERS: Final = ("api_key", "password", "secret", "token", "private key", "bearer ")


class ManualHandoffError(ValueError):
    """A manual-handoff integrity or scope boundary failed closed."""


@dataclass(frozen=True)
class ManualTaskArtifact:
    schema_version: str
    task_id: str
    repository: str
    feature_branch: str
    scope: str


@dataclass(frozen=True)
class ManualTask:
    artifact: ManualTaskArtifact
    task_digest_sha256: str
    task_status: str
    review_status: str


@dataclass(frozen=True)
class ManualResult:
    schema_version: str
    task_id: str
    task_digest_sha256: str
    outcome: str
    summary: str
    tests: str
    report_digest_sha256: str


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _opaque_id(value: object) -> bool:
    return (isinstance(value, str) and bool(value) and len(value) <= 160 and
            all(character.isalnum() or character in "._:-" for character in value))


def _sha256(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64 and
            all(character in "0123456789abcdef" for character in value))


def _safe_text(value: object, *, maximum: int = 600) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= maximum and
            "\x00" not in value and all(marker not in value.lower() for marker in FORBIDDEN_METADATA_MARKERS))


def _artifact_valid(artifact: object) -> bool:
    return (isinstance(artifact, ManualTaskArtifact) and
            artifact.schema_version == MANUAL_HANDOFF_VERSION and _opaque_id(artifact.task_id) and
            artifact.repository == ALLOWED_REPOSITORY and
            isinstance(artifact.feature_branch, str) and artifact.feature_branch.startswith("feature/") and
            artifact.feature_branch != "main" and _safe_text(artifact.scope))


def _task_valid(task: object) -> bool:
    return (isinstance(task, ManualTask) and _artifact_valid(task.artifact) and
            task.task_digest_sha256 == _digest(asdict(task.artifact)) and
            task.task_status in TASK_STATUSES and task.review_status in REVIEW_STATUSES)


def _result_digest(result: ManualResult) -> str:
    return _digest({
        "schema_version": result.schema_version,
        "task_id": result.task_id,
        "task_digest_sha256": result.task_digest_sha256,
        "outcome": result.outcome,
        "summary": result.summary,
        "tests": result.tests,
    })


def _result_valid(result: object) -> bool:
    return (isinstance(result, ManualResult) and result.schema_version == MANUAL_HANDOFF_VERSION and
            _opaque_id(result.task_id) and _sha256(result.task_digest_sha256) and
            result.outcome in {"COMPLETED", "UNCERTAIN"} and _safe_text(result.summary) and
            _safe_text(result.tests) and result.report_digest_sha256 == _result_digest(result))


class ManualHandoffStore:
    """Atomic local metadata store; reports are immutable once accepted."""

    def __init__(self, root: Path, *, repository_root: Path | None = None):
        candidate = Path(root).expanduser()
        if not candidate.is_absolute():
            raise ManualHandoffError("STORE_ROOT_MUST_BE_ABSOLUTE")
        self.root = candidate.resolve()
        if repository_root is not None and self.root.is_relative_to(Path(repository_root).expanduser().resolve()):
            raise ManualHandoffError("STORE_ROOT_INSIDE_REPOSITORY")
        self.tasks_root = self.root / "manual_tasks"
        self.results_root = self.root / "manual_results"
        self.transactions_root = self.root / "manual_transactions"
        self._ensure_directories()
        self._reconcile()

    def _ensure_directories(self) -> None:
        try:
            for path in (self.tasks_root, self.results_root, self.transactions_root):
                path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ManualHandoffError("STORE_UNAVAILABLE") from error

    @staticmethod
    def _read(path: Path) -> dict[str, object]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise ManualHandoffError("STORE_RECORD_MISSING") from error
        except (OSError, json.JSONDecodeError) as error:
            raise ManualHandoffError("STORE_CORRUPT") from error
        if not isinstance(value, dict):
            raise ManualHandoffError("STORE_CORRUPT")
        return value

    @staticmethod
    def _atomic_write(path: Path, value: object, *, create_only: bool = False) -> None:
        descriptor = -1
        temporary = ""
        try:
            descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write((_canonical_json(value) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            if create_only:
                try:
                    os.link(temporary, path)
                except FileExistsError as error:
                    raise ManualHandoffError("DUPLICATE_RECORD") from error
            else:
                os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except ManualHandoffError:
            raise
        except OSError as error:
            raise ManualHandoffError("STORE_WRITE_FAILED") from error
        finally:
            if descriptor != -1:
                os.close(descriptor)
            if temporary:
                Path(temporary).unlink(missing_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_root / f"{task_id}.json"

    def _result_path(self, task_id: str) -> Path:
        return self.results_root / f"{task_id}.json"

    def _transaction_path(self, task_id: str) -> Path:
        return self.transactions_root / f"{task_id}.json"

    @staticmethod
    def _task_from_json(value: dict[str, object]) -> ManualTask:
        if set(value) != {"artifact", "task_digest_sha256", "task_status", "review_status"} or not isinstance(value["artifact"], dict):
            raise ManualHandoffError("STORE_CORRUPT")
        try:
            task = ManualTask(ManualTaskArtifact(**value["artifact"]), value["task_digest_sha256"], value["task_status"], value["review_status"])
        except TypeError as error:
            raise ManualHandoffError("STORE_CORRUPT") from error
        if not _task_valid(task):
            raise ManualHandoffError("STORE_CORRUPT")
        return task

    @staticmethod
    def _result_from_json(value: dict[str, object]) -> ManualResult:
        expected = {"schema_version", "task_id", "task_digest_sha256", "outcome", "summary", "tests", "report_digest_sha256"}
        if set(value) != expected:
            raise ManualHandoffError("STORE_CORRUPT")
        try:
            result = ManualResult(**value)
        except TypeError as error:
            raise ManualHandoffError("STORE_CORRUPT") from error
        if not _result_valid(result):
            raise ManualHandoffError("STORE_CORRUPT")
        return result

    def _reconcile(self) -> None:
        try:
            paths = tuple(sorted(self.transactions_root.glob("*.json")))
        except OSError as error:
            raise ManualHandoffError("STORE_READ_FAILED") from error
        for path in paths:
            value = self._read(path)
            if set(value) != {"prior_task", "updated_task", "result"}:
                raise ManualHandoffError("TRANSACTION_CORRUPT")
            prior = self._task_from_json(value["prior_task"]) if isinstance(value["prior_task"], dict) else None
            updated = self._task_from_json(value["updated_task"]) if isinstance(value["updated_task"], dict) else None
            result = self._result_from_json(value["result"]) if isinstance(value["result"], dict) else None
            if prior is None or updated is None or result is None or path.stem != result.task_id:
                raise ManualHandoffError("TRANSACTION_CORRUPT")
            current = self.load_task(result.task_id)
            result_path = self._result_path(result.task_id)
            if current == prior:
                if result_path.exists():
                    if self.load_result(result.task_id) != result:
                        raise ManualHandoffError("TRANSACTION_RESULT_CONFLICT")
                else:
                    self._atomic_write(result_path, asdict(result), create_only=True)
                self._atomic_write(self._task_path(result.task_id), asdict(updated))
            elif current != updated or not result_path.exists() or self.load_result(result.task_id) != result:
                raise ManualHandoffError("TRANSACTION_CONFLICT")
            path.unlink()
        self._validate_inventory()

    def _validate_inventory(self) -> None:
        try:
            result_paths = tuple(sorted(self.results_root.glob("*.json")))
        except OSError as error:
            raise ManualHandoffError("STORE_READ_FAILED") from error
        for path in result_paths:
            result = self._result_from_json(self._read(path))
            task = self.load_task(result.task_id)
            if (path.stem != result.task_id or task.task_digest_sha256 != result.task_digest_sha256 or
                    task.task_status not in {"RESULT_REPORTED", "OUTCOME_UNCERTAIN"}):
                raise ManualHandoffError("ORPHANED_MANUAL_RESULT")

    def create_task(self, artifact: ManualTaskArtifact) -> ManualTask:
        if not _artifact_valid(artifact):
            raise ManualHandoffError("TASK_ARTIFACT_INVALID")
        task = ManualTask(artifact, _digest(asdict(artifact)), "CREATED", "NOT_REVIEWED")
        try:
            self._atomic_write(self._task_path(artifact.task_id), asdict(task), create_only=True)
        except ManualHandoffError as error:
            if str(error) == "DUPLICATE_RECORD":
                raise ManualHandoffError("DUPLICATE_TASK_ID") from None
            raise
        return task

    def load_task(self, task_id: str) -> ManualTask:
        if not _opaque_id(task_id):
            raise ManualHandoffError("TASK_ID_INVALID")
        return self._task_from_json(self._read(self._task_path(task_id)))

    def handoff(self, task_id: str) -> tuple[ManualTask, str]:
        task = self.load_task(task_id)
        if task.task_status not in {"CREATED", "HANDOFF_READY"}:
            raise ManualHandoffError("HANDOFF_NOT_ELIGIBLE")
        updated = replace(task, task_status="HANDOFF_READY")
        self._atomic_write(self._task_path(task_id), asdict(updated))
        prompt = (
            "Manual supervised Codex task. Do not start a provider automatically.\n"
            f"Repository: {task.artifact.repository}\nBranch: {task.artifact.feature_branch}\n"
            f"Task ID: {task.artifact.task_id}\nTask digest: {task.task_digest_sha256}\n"
            f"Scope: {task.artifact.scope}\n"
            "Do not modify main, merge, deploy, run workflows, use credentials, or access other repositories. "
            "Return only a concise summary and local test results to the supervising human."
        )
        return updated, prompt

    def report_result(self, result: ManualResult) -> ManualTask:
        if not _result_valid(result):
            raise ManualHandoffError("MANUAL_RESULT_INVALID")
        task = self.load_task(result.task_id)
        if task.task_status != "HANDOFF_READY" or task.task_digest_sha256 != result.task_digest_sha256:
            raise ManualHandoffError("MANUAL_RESULT_NOT_ELIGIBLE")
        updated = replace(task, task_status="RESULT_REPORTED" if result.outcome == "COMPLETED" else "OUTCOME_UNCERTAIN")
        transaction = {"prior_task": asdict(task), "updated_task": asdict(updated), "result": asdict(result)}
        try:
            self._atomic_write(self._transaction_path(result.task_id), transaction, create_only=True)
            self._atomic_write(self._result_path(result.task_id), asdict(result), create_only=True)
        except ManualHandoffError as error:
            if str(error) == "DUPLICATE_RECORD":
                raise ManualHandoffError("DUPLICATE_MANUAL_RESULT") from None
            raise
        self._atomic_write(self._task_path(result.task_id), asdict(updated))
        try:
            self._transaction_path(result.task_id).unlink()
        except OSError as error:
            raise ManualHandoffError("STORE_WRITE_FAILED") from error
        return updated

    def load_result(self, task_id: str) -> ManualResult:
        return self._result_from_json(self._read(self._result_path(task_id)))

    def review(self, task_id: str, decision: str) -> ManualTask:
        if decision not in {"APPROVED", "REJECTED"}:
            raise ManualHandoffError("REVIEW_STATUS_INVALID")
        task = self.load_task(task_id)
        if task.task_status != "RESULT_REPORTED":
            raise ManualHandoffError("REVIEW_REQUIRES_COMPLETED_RESULT")
        result = self.load_result(task_id)
        if result.task_digest_sha256 != task.task_digest_sha256 or result.outcome != "COMPLETED":
            raise ManualHandoffError("REVIEW_RESULT_INTEGRITY_FAILED")
        updated = replace(task, review_status=decision)
        self._atomic_write(self._task_path(task_id), asdict(updated))
        return updated

    def incomplete_tasks(self) -> tuple[ManualTask, ...]:
        self._reconcile()
        try:
            paths = tuple(sorted(self.tasks_root.glob("*.json")))
        except OSError as error:
            raise ManualHandoffError("STORE_READ_FAILED") from error
        return tuple(task for task in (self._task_from_json(self._read(path)) for path in paths)
                     if task.task_status in {"CREATED", "HANDOFF_READY", "OUTCOME_UNCERTAIN"})
