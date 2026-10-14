"""Persistent local task state and a future-execution dry-run preflight.

This module has no provider client, subprocess call, credential lookup, network
transport, scheduler, or task executor.  ``ALLOWED`` means only that the
synthetic offline preflight passed; it never authorizes a provider start.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Final


LOCAL_EXECUTION_VERSION: Final = "local-execution-foundation-v0.10"
CHECKPOINT_TRANSACTION_VERSION: Final = "checkpoint-transaction-v0.10"
SYNTHETIC_TASK_KIND: Final = "synthetic-local-development-task-v1"
SAFE_LOCAL_DIRECTORIES: Final = frozenset({"docs", "night_shift_pilot", "tests"})
TASK_STATUSES: Final = frozenset({
    "PENDING", "RUNNING", "PAUSED_INCOMPLETE", "UNKNOWN_PROVIDER_OUTCOME",
    "COMPLETED", "FAILED",
})
REVIEW_STATUSES: Final = frozenset({"NOT_REVIEWED", "APPROVED", "REJECTED"})
INCOMPLETE_STATUSES: Final = frozenset({
    "PENDING", "RUNNING", "PAUSED_INCOMPLETE", "UNKNOWN_PROVIDER_OUTCOME",
})


class LocalExecutionStoreError(ValueError):
    """A local persistence or validation boundary failed closed."""


@dataclass(frozen=True)
class SyntheticTaskArtifact:
    schema_version: str
    task_id: str
    task_kind: str
    input_digest_sha256: str
    allowed_repository: str
    allowed_feature_branch: str


@dataclass(frozen=True)
class StoredTask:
    artifact: SyntheticTaskArtifact
    artifact_sha256: str
    task_status: str
    review_status: str
    execution_attempt_ids: tuple[str, ...]


@dataclass(frozen=True)
class StoredCheckpoint:
    schema_version: str
    task_id: str
    execution_attempt_id: str
    task_status: str
    review_status: str
    last_confirmed_checkpoint: str
    provider_outcome_uncertain: bool


@dataclass(frozen=True)
class PreflightRequest:
    task: StoredTask
    repository: str
    feature_branch: str
    allowed_directories: tuple[str, ...]
    requested_directories: tuple[str, ...]
    emergency_stop: str | None
    human_authorized: bool
    auth_mode: str
    api_key_mode: bool
    paid_fallback_enabled: bool
    extra_credits_allowed: bool
    paid_reset_allowed: bool
    sandbox_mode: str
    automatic_merge: bool
    automatic_deployment: bool
    previous_provider_outcome_uncertain: bool


@dataclass(frozen=True)
class PreflightDecision:
    status: str
    code: str


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: object, *, maximum: int = 160) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= maximum


def _opaque_id(value: object) -> bool:
    return (_text(value) and all(character.isalnum() or character in "._:-" for character in value))


def _sha256(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64 and
            all(character in "0123456789abcdef" for character in value))


def _safe_relative_directory(value: object) -> bool:
    if not _text(value):
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and str(path) == value


def _artifact_valid(artifact: object) -> bool:
    return (isinstance(artifact, SyntheticTaskArtifact) and
            artifact.schema_version == LOCAL_EXECUTION_VERSION and
            _opaque_id(artifact.task_id) and artifact.task_kind == SYNTHETIC_TASK_KIND and
            _sha256(artifact.input_digest_sha256) and _text(artifact.allowed_repository) and
            _text(artifact.allowed_feature_branch) and
            artifact.allowed_feature_branch.startswith("feature/"))


def _stored_task_valid(task: object) -> bool:
    return (isinstance(task, StoredTask) and _artifact_valid(task.artifact) and
            task.artifact_sha256 == _digest(asdict(task.artifact)) and
            task.task_status in TASK_STATUSES and task.review_status in REVIEW_STATUSES and
            isinstance(task.execution_attempt_ids, tuple) and
            all(_opaque_id(item) for item in task.execution_attempt_ids) and
            len(task.execution_attempt_ids) == len(set(task.execution_attempt_ids)))


def _checkpoint_valid(checkpoint: object) -> bool:
    if (not isinstance(checkpoint, StoredCheckpoint) or
            checkpoint.schema_version != LOCAL_EXECUTION_VERSION or
            not _opaque_id(checkpoint.task_id) or
            not _opaque_id(checkpoint.execution_attempt_id) or
            checkpoint.task_status not in TASK_STATUSES or
            checkpoint.review_status not in REVIEW_STATUSES or
            not _opaque_id(checkpoint.last_confirmed_checkpoint) or
            not isinstance(checkpoint.provider_outcome_uncertain, bool)):
        return False
    if checkpoint.provider_outcome_uncertain:
        return checkpoint.task_status == "UNKNOWN_PROVIDER_OUTCOME"
    return checkpoint.task_status != "UNKNOWN_PROVIDER_OUTCOME"


def default_local_store_root() -> Path:
    """Return a per-user runtime location that is outside a repository by default."""
    return Path.home() / ".local" / "state" / "kaya-night-shift"


class LocalExecutionStore:
    """Atomically persist synthetic task records and immutable attempt checkpoints."""

    def __init__(self, root: Path, *, repository_root: Path | None = None):
        candidate = Path(root).expanduser()
        if not candidate.is_absolute():
            raise LocalExecutionStoreError("STORE_ROOT_MUST_BE_ABSOLUTE")
        self.root = candidate.resolve()
        if repository_root is not None:
            repository = Path(repository_root).expanduser().resolve()
            if self.root.is_relative_to(repository):
                raise LocalExecutionStoreError("STORE_ROOT_INSIDE_REPOSITORY")
        self.tasks_root = self.root / "tasks"
        self.checkpoints_root = self.root / "checkpoints"
        self.transactions_root = self.root / "transactions"
        self.reconciled_transaction_ids: tuple[str, ...] = ()
        self._ensure_directories()
        self._reconcile_storage()

    def _ensure_directories(self) -> None:
        try:
            self.tasks_root.mkdir(parents=True, exist_ok=True)
            self.checkpoints_root.mkdir(parents=True, exist_ok=True)
            self.transactions_root.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise LocalExecutionStoreError("STORE_UNAVAILABLE") from error

    @staticmethod
    def _atomic_write(path: Path, value: object) -> None:
        encoded = (_canonical_json(value) + "\n").encode("utf-8")
        descriptor = -1
        temporary_name = ""
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as error:
            raise LocalExecutionStoreError("STORE_WRITE_FAILED") from error
        finally:
            if descriptor != -1:
                os.close(descriptor)
            if temporary_name:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _atomic_create(path: Path, value: object) -> None:
        """Create an immutable record without a check-then-overwrite race."""
        encoded = (_canonical_json(value) + "\n").encode("utf-8")
        descriptor = -1
        temporary_name = ""
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary_name, path)
            except FileExistsError as error:
                raise LocalExecutionStoreError("DUPLICATE_RECORD") from error
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except LocalExecutionStoreError:
            raise
        except OSError as error:
            raise LocalExecutionStoreError("STORE_WRITE_FAILED") from error
        finally:
            if descriptor != -1:
                os.close(descriptor)
            if temporary_name:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise LocalExecutionStoreError("STORE_RECORD_MISSING") from error
        except OSError as error:
            raise LocalExecutionStoreError("STORE_READ_FAILED") from error
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise LocalExecutionStoreError("STORE_CORRUPT") from error
        if not isinstance(value, dict):
            raise LocalExecutionStoreError("STORE_CORRUPT")
        return value

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_root / f"{task_id}.json"

    def _checkpoint_path(self, attempt_id: str) -> Path:
        """Execution-attempt IDs are unique across the complete local store."""
        return self.checkpoints_root / f"{attempt_id}.json"

    def _transaction_path(self, attempt_id: str) -> Path:
        return self.transactions_root / f"{attempt_id}.json"

    @staticmethod
    def _task_to_json(task: StoredTask) -> dict[str, object]:
        return {
            "artifact": asdict(task.artifact),
            "artifact_sha256": task.artifact_sha256,
            "execution_attempt_ids": list(task.execution_attempt_ids),
            "review_status": task.review_status,
            "task_status": task.task_status,
        }

    @staticmethod
    def _task_from_json(value: dict[str, object]) -> StoredTask:
        expected = {"artifact", "artifact_sha256", "execution_attempt_ids", "review_status", "task_status"}
        if set(value) != expected or not isinstance(value["artifact"], dict):
            raise LocalExecutionStoreError("STORE_CORRUPT")
        try:
            artifact = SyntheticTaskArtifact(**value["artifact"])
            attempt_ids = value["execution_attempt_ids"]
            task = StoredTask(artifact, value["artifact_sha256"], value["task_status"],
                              value["review_status"], tuple(attempt_ids))
        except (TypeError, ValueError) as error:
            raise LocalExecutionStoreError("STORE_CORRUPT") from error
        if not _stored_task_valid(task):
            raise LocalExecutionStoreError("STORE_CORRUPT")
        return task

    @staticmethod
    def _checkpoint_to_json(checkpoint: StoredCheckpoint) -> dict[str, object]:
        return asdict(checkpoint)

    @staticmethod
    def _checkpoint_from_json(value: dict[str, object]) -> StoredCheckpoint:
        expected = {
            "schema_version", "task_id", "execution_attempt_id", "task_status",
            "review_status", "last_confirmed_checkpoint", "provider_outcome_uncertain",
        }
        if set(value) != expected:
            raise LocalExecutionStoreError("STORE_CORRUPT")
        try:
            checkpoint = StoredCheckpoint(**value)
        except TypeError as error:
            raise LocalExecutionStoreError("STORE_CORRUPT") from error
        if not _checkpoint_valid(checkpoint):
            raise LocalExecutionStoreError("STORE_CORRUPT")
        return checkpoint

    @classmethod
    def _transaction_to_json(cls, prior_task: StoredTask, updated_task: StoredTask,
                             checkpoint: StoredCheckpoint) -> dict[str, object]:
        return {
            "checkpoint": cls._checkpoint_to_json(checkpoint),
            "prior_task": cls._task_to_json(prior_task),
            "schema_version": CHECKPOINT_TRANSACTION_VERSION,
            "updated_task": cls._task_to_json(updated_task),
        }

    @classmethod
    def _transaction_from_json(cls, value: dict[str, object]) -> tuple[StoredTask, StoredTask, StoredCheckpoint]:
        expected = {"checkpoint", "prior_task", "schema_version", "updated_task"}
        if (set(value) != expected or value["schema_version"] != CHECKPOINT_TRANSACTION_VERSION or
                not isinstance(value["checkpoint"], dict) or
                not isinstance(value["prior_task"], dict) or
                not isinstance(value["updated_task"], dict)):
            raise LocalExecutionStoreError("TRANSACTION_CORRUPT")
        try:
            checkpoint = cls._checkpoint_from_json(value["checkpoint"])
            prior_task = cls._task_from_json(value["prior_task"])
            updated_task = cls._task_from_json(value["updated_task"])
        except LocalExecutionStoreError as error:
            raise LocalExecutionStoreError("TRANSACTION_CORRUPT") from error
        if (prior_task.artifact != updated_task.artifact or
                checkpoint.task_id != prior_task.artifact.task_id or
                checkpoint.execution_attempt_id in prior_task.execution_attempt_ids or
                updated_task.execution_attempt_ids !=
                prior_task.execution_attempt_ids + (checkpoint.execution_attempt_id,) or
                updated_task.task_status != checkpoint.task_status or
                updated_task.review_status != checkpoint.review_status):
            raise LocalExecutionStoreError("TRANSACTION_CORRUPT")
        return prior_task, updated_task, checkpoint

    @staticmethod
    def _remove_transaction(path: Path) -> None:
        try:
            path.unlink()
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except FileNotFoundError as error:
            raise LocalExecutionStoreError("TRANSACTION_MISSING") from error
        except OSError as error:
            raise LocalExecutionStoreError("STORE_WRITE_FAILED") from error

    def _reconcile_storage(self) -> None:
        """Finish only exact, journaled checkpoint commits; reject every other split state."""
        try:
            transaction_paths = tuple(sorted(self.transactions_root.glob("*.json")))
        except OSError as error:
            raise LocalExecutionStoreError("STORE_READ_FAILED") from error
        reconciled: list[str] = []
        for path in transaction_paths:
            prior_task, updated_task, checkpoint = self._transaction_from_json(self._read_json(path))
            if path.stem != checkpoint.execution_attempt_id:
                raise LocalExecutionStoreError("TRANSACTION_CORRUPT")
            current_task = self.load_task(checkpoint.task_id)
            checkpoint_path = self._checkpoint_path(checkpoint.execution_attempt_id)
            if current_task == prior_task:
                if checkpoint_path.exists():
                    existing = self.load_checkpoint(checkpoint.task_id, checkpoint.execution_attempt_id)
                    if existing != checkpoint:
                        raise LocalExecutionStoreError("TRANSACTION_CHECKPOINT_CONFLICT")
                else:
                    try:
                        self._atomic_create(checkpoint_path, self._checkpoint_to_json(checkpoint))
                    except LocalExecutionStoreError as error:
                        if str(error) == "DUPLICATE_RECORD":
                            raise LocalExecutionStoreError("TRANSACTION_CHECKPOINT_CONFLICT") from None
                        raise
                self._atomic_write(self._task_path(checkpoint.task_id), self._task_to_json(updated_task))
            elif current_task == updated_task:
                if not checkpoint_path.exists():
                    raise LocalExecutionStoreError("TRANSACTION_CHECKPOINT_MISSING")
                existing = self.load_checkpoint(checkpoint.task_id, checkpoint.execution_attempt_id)
                if existing != checkpoint:
                    raise LocalExecutionStoreError("TRANSACTION_CHECKPOINT_CONFLICT")
            else:
                raise LocalExecutionStoreError("TRANSACTION_TASK_CONFLICT")
            self._remove_transaction(path)
            reconciled.append(checkpoint.execution_attempt_id)
        self.reconciled_transaction_ids = tuple(reconciled)
        self._validate_checkpoint_inventory()

    def _validate_checkpoint_inventory(self) -> None:
        """Reject checkpoints not bound to a task record after transaction recovery."""
        try:
            task_paths = tuple(sorted(self.tasks_root.glob("*.json")))
            checkpoint_paths = tuple(sorted(self.checkpoints_root.glob("*.json")))
        except OSError as error:
            raise LocalExecutionStoreError("STORE_READ_FAILED") from error
        bound_attempts: set[str] = set()
        for path in task_paths:
            task = self._task_from_json(self._read_json(path))
            if path.stem != task.artifact.task_id:
                raise LocalExecutionStoreError("STORE_CORRUPT")
            for attempt_id in task.execution_attempt_ids:
                checkpoint = self.load_checkpoint(task.artifact.task_id, attempt_id)
                if checkpoint.execution_attempt_id != attempt_id:
                    raise LocalExecutionStoreError("STORE_CORRUPT")
                bound_attempts.add(attempt_id)
        for path in checkpoint_paths:
            checkpoint = self._checkpoint_from_json(self._read_json(path))
            if path.stem != checkpoint.execution_attempt_id:
                raise LocalExecutionStoreError("STORE_CORRUPT")
            if checkpoint.execution_attempt_id not in bound_attempts:
                raise LocalExecutionStoreError("ORPHANED_CHECKPOINT")

    def create_task(self, artifact: SyntheticTaskArtifact, *, task_status: str = "PENDING",
                    review_status: str = "NOT_REVIEWED") -> StoredTask:
        if not _artifact_valid(artifact) or task_status not in TASK_STATUSES or review_status not in REVIEW_STATUSES:
            raise LocalExecutionStoreError("TASK_ARTIFACT_INVALID")
        path = self._task_path(artifact.task_id)
        if path.exists():
            raise LocalExecutionStoreError("DUPLICATE_TASK_ID")
        task = StoredTask(artifact, _digest(asdict(artifact)), task_status, review_status, ())
        try:
            self._atomic_create(path, self._task_to_json(task))
        except LocalExecutionStoreError as error:
            if str(error) == "DUPLICATE_RECORD":
                raise LocalExecutionStoreError("DUPLICATE_TASK_ID") from None
            raise
        return task

    def load_task(self, task_id: str) -> StoredTask:
        if not _opaque_id(task_id):
            raise LocalExecutionStoreError("TASK_ID_INVALID")
        return self._task_from_json(self._read_json(self._task_path(task_id)))

    def save_checkpoint(self, checkpoint: StoredCheckpoint) -> StoredTask:
        if not _checkpoint_valid(checkpoint):
            raise LocalExecutionStoreError("CHECKPOINT_INVALID")
        task = self.load_task(checkpoint.task_id)
        if (task.task_status == "UNKNOWN_PROVIDER_OUTCOME" and
                checkpoint.task_status != "UNKNOWN_PROVIDER_OUTCOME"):
            raise LocalExecutionStoreError("UNRESOLVED_PROVIDER_OUTCOME")
        if checkpoint.execution_attempt_id in task.execution_attempt_ids:
            raise LocalExecutionStoreError("DUPLICATE_EXECUTION_ATTEMPT_ID")
        checkpoint_path = self._checkpoint_path(checkpoint.execution_attempt_id)
        if checkpoint_path.exists():
            raise LocalExecutionStoreError("DUPLICATE_EXECUTION_ATTEMPT_ID")
        try:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise LocalExecutionStoreError("STORE_UNAVAILABLE") from error
        updated = replace(
            task,
            task_status=checkpoint.task_status,
            review_status=checkpoint.review_status,
            execution_attempt_ids=task.execution_attempt_ids + (checkpoint.execution_attempt_id,),
        )
        transaction_path = self._transaction_path(checkpoint.execution_attempt_id)
        try:
            self._atomic_create(
                transaction_path,
                self._transaction_to_json(task, updated, checkpoint),
            )
        except LocalExecutionStoreError as error:
            if str(error) == "DUPLICATE_RECORD":
                raise LocalExecutionStoreError("DUPLICATE_EXECUTION_ATTEMPT_ID") from None
            raise
        try:
            self._atomic_create(checkpoint_path, self._checkpoint_to_json(checkpoint))
        except LocalExecutionStoreError as error:
            if str(error) == "DUPLICATE_RECORD":
                raise LocalExecutionStoreError("DUPLICATE_EXECUTION_ATTEMPT_ID") from None
            raise
        self._atomic_write(self._task_path(checkpoint.task_id), self._task_to_json(updated))
        self._remove_transaction(transaction_path)
        return updated

    def load_checkpoint(self, task_id: str, attempt_id: str) -> StoredCheckpoint:
        if not _opaque_id(task_id) or not _opaque_id(attempt_id):
            raise LocalExecutionStoreError("CHECKPOINT_ID_INVALID")
        checkpoint = self._checkpoint_from_json(self._read_json(self._checkpoint_path(attempt_id)))
        if checkpoint.task_id != task_id:
            raise LocalExecutionStoreError("CHECKPOINT_TASK_MISMATCH")
        return checkpoint

    def recover_incomplete(self) -> tuple[tuple[StoredTask, StoredCheckpoint | None], ...]:
        self._reconcile_storage()
        try:
            paths = tuple(sorted(self.tasks_root.glob("*.json")))
        except OSError as error:
            raise LocalExecutionStoreError("STORE_READ_FAILED") from error
        recovered: list[tuple[StoredTask, StoredCheckpoint | None]] = []
        for path in paths:
            task = self._task_from_json(self._read_json(path))
            if task.task_status in INCOMPLETE_STATUSES:
                checkpoint = (self.load_checkpoint(task.artifact.task_id, task.execution_attempt_ids[-1])
                              if task.execution_attempt_ids else None)
                recovered.append((task, checkpoint))
        return tuple(recovered)


def dry_run_preflight(request: object) -> PreflightDecision:
    """Evaluate only offline boundaries for a hypothetical future local start."""
    if not isinstance(request, PreflightRequest) or not _stored_task_valid(request.task):
        return PreflightDecision("DENIED", "PREFLIGHT_REQUEST_INVALID")
    if request.emergency_stop != "false":
        return PreflightDecision("DENIED", "NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE")
    if request.human_authorized is not True or request.task.review_status != "APPROVED":
        return PreflightDecision("DENIED", "HUMAN_AUTHORIZATION_REQUIRED")
    artifact = request.task.artifact
    if (artifact.task_kind != SYNTHETIC_TASK_KIND or
            request.task.task_status not in {"PENDING", "PAUSED_INCOMPLETE"}):
        return PreflightDecision("DENIED", "SYNTHETIC_TASK_NOT_ELIGIBLE")
    if (not _text(request.repository) or request.repository != artifact.allowed_repository):
        return PreflightDecision("DENIED", "REPOSITORY_NOT_ALLOWED")
    if (not _text(request.feature_branch) or request.feature_branch == "main" or
            not request.feature_branch.startswith("feature/") or
            request.feature_branch != artifact.allowed_feature_branch):
        return PreflightDecision("DENIED", "FEATURE_BRANCH_REQUIRED")
    if (not isinstance(request.allowed_directories, tuple) or
            not isinstance(request.requested_directories, tuple) or
            not request.requested_directories or
            not all(_safe_relative_directory(item) and item in SAFE_LOCAL_DIRECTORIES
                    for item in request.allowed_directories) or
            not set(request.requested_directories).issubset(set(request.allowed_directories))):
        return PreflightDecision("DENIED", "DIRECTORY_SCOPE_INVALID")
    if request.auth_mode != "chatgpt_subscription" or request.api_key_mode is not False:
        return PreflightDecision("DENIED", "API_KEY_MODE_FORBIDDEN")
    if not all(value is False for value in (
        request.paid_fallback_enabled, request.extra_credits_allowed,
        request.paid_reset_allowed, request.automatic_merge, request.automatic_deployment,
    )):
        return PreflightDecision("DENIED", "PAID_OR_AUTOMATIC_PATH_FORBIDDEN")
    if request.sandbox_mode != "workspace-write":
        return PreflightDecision("DENIED", "SANDBOX_SCOPE_INVALID")
    if (not isinstance(request.previous_provider_outcome_uncertain, bool) or
            request.previous_provider_outcome_uncertain or
            request.task.task_status == "UNKNOWN_PROVIDER_OUTCOME"):
        return PreflightDecision("DENIED", "PREVIOUS_PROVIDER_OUTCOME_UNCERTAIN")
    return PreflightDecision("ALLOWED", "OFFLINE_PREFLIGHT_ONLY")
