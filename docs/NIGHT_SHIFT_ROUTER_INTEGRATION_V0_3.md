# Night Shift Router Integration v0.3

## Scope

Version 0.3 connects the existing public Night Shift MOCK controller to the
deterministic Intelligent Engine Router. It remains a synthetic, local decision
integration: it does not call an AI provider, use credentials, execute task
content, publish GitHub changes, deploy, or schedule work.

The workflow remains manual-only (`workflow_dispatch`), main-only, read-only,
and uses the existing pinned official actions. The repository variable
`NIGHT_SHIFT_STOP` is intentionally unchanged and currently `true`; only the
exact value `false` permits any mock phase to proceed.

## Data flow

1. The controller validates manual dispatch, `main`, the emergency stop, branch
   protection, and the sole allowlisted synthetic task.
2. It creates the existing fixed task spec and maps that specific task to an
   explicit router `TaskSpec`: documentation, complexity 1, low risk, `writing`
   capability, baseline quality, zero synthetic budget, and no paid approval.
3. The router evaluates only fixed mock-only profiles. The controller blocks on
   `NO_EXECUTION`, an unknown engine, or a non-mock engine.
4. `prepared.json` carries the spec, the serialised candidate audit, selected
   engine, rationale, fallback IDs, router-task digest, router-decision digest,
   and a prepared-handoff digest bound to the spec and router decision.
5. The deterministic worker revalidates the full prepared handoff before it
   returns a synthetic result. Its result binds the task, selected mock engine,
   router-decision digest, and a result digest.
6. Finalization revalidates the prepared handoff and all worker bindings before
   producing `MOCK_COMPLETED_NO_PUBLICATION`.

The existing artifact transport already transfers `prepared.json` between the
three jobs, so no workflow permission, trigger, action, or network change is
needed for v0.3.

## Trust boundaries and integrity

SHA-256 here detects accidental or unauthorised artifact changes within the
existing trusted workflow boundary; it is not authentication and cannot by
itself protect against an actor able to replace every artifact and digest. To
avoid accepting a self-consistent changed routing result, validation also
reconstructs the router task and recomputes the exact deterministic decision
from immutable in-repository mock profiles. The GitHub workflow's pinned
checkout, read-only permissions, fixed main ref, and artifact boundary remain
the relevant trust controls.

## Fail-closed codes

Examples of structured stop codes are:

- `NIGHT_SHIFT_STOP_NOT_EXPLICITLY_FALSE`
- `TASK_NOT_PREAPPROVED` and `ROUTER_TASK_NOT_APPROVED`
- `ROUTER_NO_EXECUTION`, `ROUTER_ENGINE_UNKNOWN`, and
  `ROUTER_ENGINE_NOT_MOCK_ONLY`
- `ROUTER_HANDOFF_MISSING`, `ROUTER_TASK_ID_MISMATCH`,
  `ROUTER_DECISION_INTEGRITY_FAILED`, and `ROUTER_DECISION_MISMATCH`
- `PREPARED_HANDOFF_CONTRACT_INVALID` and `PREPARED_HANDOFF_INTEGRITY_FAILED`
- `WORKER_ROUTER_RESULT_MISMATCH` and `WORKER_RESULT_INTEGRITY_FAILED`

No routing result is execution authority. The fixed controller/environment
checks must pass independently, and every phase repeats the emergency-stop
guard.

## Local verification

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile night_shift_pilot/*.py scripts/*.py
```

The test suite uses synthetic fixtures only. It covers normal routing,
determinism and fallback audit, `NO_EXECUTION`, active stop, invalid allowlist,
unknown/non-mock engines, changed prepared/router handoffs, changed worker
results, task-ID mismatch, and existing public-pilot safeguards.

## Limitations and v0.4

The adapter supports exactly one hard-coded public synthetic task and fixed
mock profiles. It intentionally has no dynamic task input, live provider
availability, credentials, capacity reservation outside a simulation, or model
execution. A later version would need a separately reviewed, authenticated
handoff design and explicit provider/billing approvals before considering any
non-mock integration.
