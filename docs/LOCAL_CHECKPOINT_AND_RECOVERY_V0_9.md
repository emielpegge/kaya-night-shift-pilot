# Local checkpoint and recovery design v0.9

## Checkpoint requirements

A future local implementation must preserve, before any recovery decision:

- immutable task ID, version, and digest;
- selected provider and exact execution-attempt ID;
- isolated feature-branch/ref and permitted repository identity;
- last confirmed checkpoint and review state;
- current quota state, trusted evidence time, and reported reset metadata;
- whether a provider result may still be in flight or unknown;
- the unique recheck idempotency key and bounded attempt count;
- a new, separately required human authorization for any continuation.

The existing `TaskCheckpoint`, `QuotaDecision`, `RecheckPlan`, and
`ResumeCandidate` contracts model these fields with synthetic data. They never
perform a task start or continuation.

## Recovery simulation

| Offline condition | Required state | Recovery result |
| --- | --- | --- |
| Valid fresh capacity | `AVAILABLE` | Candidate only; no task authorization |
| Five-hour limit | `LIMIT_REACHED_5H` | Pause and plan at most one conceptual recheck |
| Weekly limit | `LIMIT_REACHED_WEEKLY` | Pause; five-hour recovery cannot clear it |
| Both limits | Weekly display plus both blockers | Earliest recheck still requires a fresh full read |
| Missing/invalid/stale evidence | `QUOTA_UNKNOWN` | No plan or task start; manual review |
| Reset time passed | No inferred capacity | Fresh evidence required |
| Emergency stop | `BLOCKED` | Stop overrides capacity and resume candidate |
| Possible in-flight result | `PAUSED_INCOMPLETE` | Do not retry or release the attempt |
| Credit fallback or paid path | Denied/manual review | No alternate route |

These cases are exercised by the v0.6/v0.7 offline tests. No new provider
simulation is added because that would not prove the source, entitlement, or
cost guarantees that a real connector requires.

## CLI session continuity is not automatic KAYA recovery

The [Codex CLI guide](https://learn.chatgpt.com/docs/cli) documents resuming
saved chats. That client feature does not bind a resumed task to KAYA's immutable
task artifact, financial policy, quota evidence, feature branch, review status,
or human authorization. It must therefore not be treated as automatic Night
Shift recovery.
