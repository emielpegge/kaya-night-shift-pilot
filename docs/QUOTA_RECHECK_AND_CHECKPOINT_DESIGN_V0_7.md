# Quota recheck and checkpoint design v0.7

## Offline-only recheck planner

When a normalized decision contains a reached limit and future provider reset
timestamps, `plan_recheck()` produces one conceptual read-only check at the
earliest relevant reset plus five seconds. It uses a deterministic SHA-256
idempotency key derived from checkpoint, target time and attempt. It starts no
timer, scheduler, background job, provider process, request or task.

If multiple limits are reached, the earliest reset can be meaningfully checked,
but a remaining weekly limit continues to block. If a read fails in a future
connector, `backoff_recheck()` models 60-second exponential backoff, capped at
900 seconds and five attempts. Exhaustion means manual review; no uncontrolled
polling. A reset time already passed without fresh evidence produces no plan.

```text
limit -> checkpoint -> conceptual read-only plan -> fresh full quota read
                                           |                 |
                                           v                 v
                                   no model/task         AVAILABLE or block
```

## Checkpoint contract

`TaskCheckpoint` binds task ID/digest, provider, latest confirmed checkpoint,
execution status, possible pending provider outcome, quota state, evidence time,
reported resets, review status, continuation authorization and execution attempt
ID. A quota block creates `PAUSED_INCOMPLETE`; it never changes an incomplete
task to completed and clears any continuation authorization.

`assess_resume_candidate()` can only produce
`CANDIDATE_REQUIRES_NEW_AUTHORIZATION` when the emergency stop is exactly false,
the task is paused/incomplete, no provider outcome may remain pending, and fresh
trusted capacity is available. It always returns `task_start_authorized: false`.
Thus the three decisions are distinct:

1. Capacity became available.
2. The paused task is a safe candidate to consider.
3. A human separately authorizes a new execution.

No v0.7 function performs step 3 or resumes work.
