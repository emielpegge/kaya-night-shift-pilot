# Codex subscription-only v0.6 Go/No-Go

## Current decision: NO-GO for unmanaged execution

KAYA permits only already included subscription allowance. This excludes every
API or paid-continuation route. The official Codex surfaces support account-plan
use and show account-specific usage, but v0.6 has no proven, security-reviewed,
unattended subscription automation path. Therefore Night Shift cannot start or
resume a provider task on its own.

| Gate | Current status | Required for a future manually supervised synthetic test |
| --- | --- | --- |
| Subscription path | Official client paths documented. | Named official client, owner account and plan eligibility confirmed. |
| API separation | Confirmed. | No API key, billing, credits, reset, upgrade or fallback option is configured. |
| Capacity | Dashboard/CLI/App Server surfaces documented, account-specific. | Fresh authoritative capacity state: `AVAILABLE`; no inferred quota from time or history. |
| Limit handling | Policy and offline tests exist. | Checkpoint and block on every non-`AVAILABLE` state; no auto-resume. |
| Authorization | Design only. | Separate human start authorization bound to one synthetic task. |
| Privacy | Synthetic-only boundary designed. | Confirm no KAYA/private content is presented to the client. |
| Safety review | Not performed. | Independent review of manual process, retention and account handling. |
| Claude | Not integrated. | Equivalent official subscription/quota/privacy evidence; otherwise remain `QUOTA_UNKNOWN`. |

## State policy

| State | New work | Recovery |
| --- | --- | --- |
| `AVAILABLE` | Only after explicit human authorization. | One bounded synthetic task only. |
| `LIMIT_REACHED_5H` | Blocked. | Checkpoint; `WAITING_FOR_RESET`. |
| `LIMIT_REACHED_WEEKLY` | Blocked. | Checkpoint; `WAITING_FOR_RESET`. |
| `QUOTA_UNKNOWN` | Blocked. | `MANUAL_REVIEW_REQUIRED`. |
| `PAUSED` | Blocked. | Human explicitly unpauses only after fresh capacity check. |
| `WAITING_FOR_RESET` | Blocked. | Never auto-resumes; fresh read plus new authorization required. |
| `MANUAL_REVIEW_REQUIRED` | Blocked. | Resolve evidence/policy conflict without a paid workaround. |

## Permanent no-cost constraints

No provider action may buy or consume credits, purchase a reset, trigger a
checkout, upgrade a plan, choose an API key, use pay-as-you-go, use another
account or select a provider/model fallback that costs more. A UI option's
availability never grants KAYA permission to use it.

The public pilot stays mock-only. `NIGHT_SHIFT_STOP` and existing live denials
remain unchanged. A future exception to this policy requires a new, explicit
owner decision and a separate security review; it cannot be inferred from a
quota reset or from an existing subscription.
