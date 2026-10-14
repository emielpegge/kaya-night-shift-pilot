# Local execution foundation v0.10

`night_shift_pilot.local_execution` adds local, standard-library-only state for
synthetic future development tasks. It has no provider, Codex subprocess,
credential lookup, network client, scheduler, or executor.

`LocalExecutionStore` requires an absolute runtime path and rejects a path
inside the supplied repository root. Its default location is the per-user
runtime path returned by `default_local_store_root()`, outside Git. Task records
and attempt checkpoints are JSON, atomically written, schema/digest verified,
and fail closed on missing or corrupt data. Attempt IDs are immutable and unique
across the local store; an uncertain provider outcome can only be stored as
`UNKNOWN_PROVIDER_OUTCOME`, never `COMPLETED` or silently cleared.

Checkpoint commits use a short journal: checkpoint and task state are reconciled
on restart only when the journal, checkpoint, and exact task transition agree.
An unjournaled or conflicting checkpoint is blocked rather than inferred.

`dry_run_preflight()` accepts only an approved synthetic task on its recorded
`feature/` branch and repository, with workspace-only sandbox scope, explicit
human authorization, exact `NIGHT_SHIFT_STOP=false`, no API-key mode, no paid
path, no automatic merge/deployment, and no uncertain earlier result. Its sole
success result is `ALLOWED / OFFLINE_PREFLIGHT_ONLY`; it does not start Codex or
grant provider permission.
