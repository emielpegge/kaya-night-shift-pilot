# Local subscription execution boundary v0.9

## Offline architecture only

```text
human-approved synthetic task
          |
          v
offline authorization + emergency-stop policy
          |
          v
v0.7 trusted quota decision ----> checkpoint/recheck model
          |                                |
          +---- never starts a provider ----+
```

The existing contracts continue to deny live execution with
`LIVE_EXECUTION_NOT_IMPLEMENTED`. A router decision, quota decision, reset
timestamp, checkpoint, or resume candidate is not a provider authorization.

## Future sequence to be proved before any live trial

1. Obtain fresh, source-trusted evidence for every applicable quota category.
2. Reject partial, stale, future, conflicting, API-key, or untrusted evidence.
3. Confirm a distinct human authorization for one immutable task digest.
4. Confirm the emergency stop is inactive and all no-cost conditions are
   independently proven.
5. If capacity becomes unavailable, preserve an incomplete checkpoint rather
   than marking the task complete.
6. Record the provider-reported reset as metadata only; schedule at most one
   conceptual read-only recheck.
7. After the reset, require a new full read of both five-hour and weekly
   categories when applicable.
8. At most mark a task as a resume candidate; require a new human authorization
   before any future execution decision.

Steps 1, 4, and any actual provider action are deliberately absent from v0.9.

## Subscription-only limits

The [pricing documentation](https://learn.chatgpt.com/docs/pricing) states that
limit estimates are not fixed and current limits/reset times must be checked in
the relevant account dashboard. It also states that a turn already active at a
usage limit may continue subject to fair-use controls. Therefore a future local
controller cannot treat a limit observation as proof that an in-flight provider
turn stopped. Its provider outcome must remain unknown, reserved, and
non-retryable until independently reconciled.

The required v0.7 state machine covers available capacity, five-hour/weekly
blocks, unknown quota, pause, conceptual wait, manual review, bounded recheck,
and idempotency. It provides no scheduler, timer, connection, or automatic
resume.

## Disallowed control paths

The boundary rejects API keys, pay-as-you-go, purchased/earned/banked credits,
credit fallback, paid resets, upgrades, alternate accounts, provider fallback,
App Server mutation methods, and model calls made solely to probe capacity.
No local controller may be introduced until a route-specific guard proves these
paths cannot be reached.
