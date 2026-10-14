# Subscription quota safety v0.7

## Non-negotiable policy

Additional AI cost is zero. KAYA never buys/consumes credits, calls an API,
uses pay-as-you-go, pays for a reset, upgrades, uses another account or selects
a cost-bearing fallback. Codex subscription use and API-key use are distinct;
the latter is explicitly excluded. [ChatGPT pricing](https://learn.chatgpt.com/docs/pricing)

The generic contract is provider-neutral. Codex has an offline normalizer only;
Claude has no adapter or quota endpoint assumption. Until official Claude
subscription quota evidence is separately verified, it is `QUOTA_UNKNOWN`.

## Required states

| State | Effect |
| --- | --- |
| `AVAILABLE` | Capacity appears available from trusted, fresh evidence; it is not task authorization. |
| `LIMIT_REACHED_5H` | Stop new work; checkpoint and conceptually wait. |
| `LIMIT_REACHED_WEEKLY` | Stop new work; checkpoint and conceptually wait. |
| `QUOTA_UNKNOWN` | Stop new work; manual review. |
| `PAUSED` | Human/emergency pause wins over capacity. |
| `WAITING_FOR_RESET` | Metadata only; never auto-resumes. |
| `MANUAL_REVIEW_REQUIRED` | Resolve policy, source or quota conflict with no paid workaround. |

## Threat model

| Threat | Required mitigation |
| --- | --- |
| API-key or paid auth mode | Reject auth/access mode before interpretation. |
| Forged/local JSON | Require connector-level source attestation; a valid schema is not source proof. |
| Stale, future or replayed event | 300-second maximum age, monotonic receipt/audit design, idempotency key. |
| Unknown/missing quota bucket | `QUOTA_UNKNOWN`; never infer capacity from a single window. |
| Reset timestamp is wrong | Re-read all required buckets after reset; timestamp alone has no capacity meaning. |
| Credit/reset option appears | Manual review; no consume/purchase action exists in the allowlist. |
| Account takeover/token leakage | Future local connector needs MFA, OS credential store, least privilege and redacted logs; v0.7 stores no token. |
| Provider outage | Preserve checkpoint; block, back off boundedly and require review after exhaustion. |
| Auto-resume | Capacity, resume candidacy and authorization are separate decisions. |

No quota payload, plan type, email, token, account ID or raw notification may be
committed to this public repository.
