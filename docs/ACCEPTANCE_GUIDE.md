# Public Night Shift MOCK pilot: acceptance guide

This repository is intentionally independent and public. It contains only generic
Python code and a fixed synthetic task. It has no service credentials, datasets,
private repository references, deployment steps, schedulers, model clients, or
paid API calls.

## What the workflow proves

`Public Night Shift MOCK pilot` is manual-only. A read-only controller accepts
only the fixed task `synthetic-documentation-check-v1`, checks that execution is
on protected `main`, and creates a local JSON handoff artifact. A separate,
deterministic worker returns a fixed synthetic result. The controller then checks
the handoff and emits a final artifact report. It never creates a commit, branch,
pull request, deployment, release, schedule, or external AI request.

The controller checks `NIGHT_SHIFT_STOP` before prepare and finalization; the
worker checks it before processing. Execution is allow-only: only the exact value
`false` permits it. Missing, empty, whitespace-padded, mixed-case, `true`, and
all other values block safely. An interruption creates no remote state: do not
rerun automatically; inspect any available artifact and authorize a new manual
attempt separately.

## Preconditions for a later, separately approved run

1. Confirm `main` remains protected with admin enforcement and no force-push or
   deletion allowance.
2. Confirm Actions retain the official four-action allowlist, full-SHA pinning,
   read-only default permissions, and disabled Actions PR approval.
3. Confirm `NIGHT_SHIFT_STOP=true` for a first blocked-path verification.
4. For one successful synthetic acceptance run only, an owner must separately
   approve temporarily setting the variable to `false`; restore `true` directly
   after observing the final report. This repository has no scheduled trigger.
5. Dispatch only from `main`, select the sole task option, and record the run ID.

## Acceptance criteria

- With the stop variable true, absent, empty, or invalid: `controller-prepare`
  ends with `BLOCKED` and code `NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE`; the
  worker does not run.
- With the stop variable false and protection visible: controller, worker and
  finalizer complete, and the final artifact reports
  `MOCK_COMPLETED_NO_PUBLICATION`.
- No branch, commit, pull request, deployment, release, schedule, credential,
  model, or paid API activity is created.

Stop immediately if protected-branch metadata is unreadable, any write permission
appears, a non-official action is requested, or an unexpected workflow job runs.
