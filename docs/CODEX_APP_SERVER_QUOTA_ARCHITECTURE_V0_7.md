# Codex App Server quota architecture v0.7

Verified against official OpenAI documentation on **2026-10-14**. v0.7 is an
offline contract and test suite. It does not start `codex app-server`, authenticate,
read a quota, start a model, use a token, or schedule a process.

## Official interface findings

The App Server documents `account/read`, `account/rateLimits/read`, and the
server notification `account/rateLimits/updated`. `account/read` reports account
type and, when available, `planType`; quota reads return the backward-compatible
single `rateLimits` bucket and optional `rateLimitsByLimitId` multi-bucket map.
Each bucket has a `limitId`, `primary`, optional `secondary`, and optional
`rateLimitReachedType`. Windows contain `usedPercent`, `windowDurationMins` and
`resetsAt`. App Server says `rateLimitsByLimitId` is keyed by metered limit ID,
and does not prescribe KAYA's logical five-hour/weekly labels or fixed durations.
[Official App Server reference](https://learn.chatgpt.com/docs/app-server)

`resetsAt` is a provider timestamp for a next reset, not proof that new capacity
exists. A fresh full read is still required after it. Quota/event availability,
plan type and values are account-dependent.

## Authentication boundary

App Server documents ChatGPT-managed authentication, external ChatGPT tokens,
API-key mode, and other modes. The quota monitor accepts only a future connector
attestation of `authMode: chatgpt` plus `access_mode: CHATGPT_SUBSCRIPTION`.
API-key mode is rejected. A parsed object alone is insufficient: the future
connector must bind trusted source, observed time, account subscription context,
and exact relevant buckets.

The documentation also says App Server authentication has not been permitted for
commercial or hosted services. That is a blocking constraint for an unattended
hosted Night Shift. Any later experiment must first obtain explicit approval for
a supported local use case; v0.7 does not claim that approval.

## Read-only allowlist

Only these future operations have an offline allowlist contract:

| Kind | Allowed |
| --- | --- |
| Request | `account/read` |
| Request | `account/rateLimits/read` |
| Notification received | `account/rateLimits/updated` |

All other requests are denied, including login, logout, `account/usage/read`,
`account/rateLimitResetCredit/consume` and
`account/sendAddCreditsNudgeEmail`. Credits, paid reset, plan upgrade,
alternative account, API key and model request are permanently outside this
allowlist. The presence of `rateLimitResetCredits` leads to manual review; it
never leads to a consume operation.

## Contract interpretation

`ProviderQuotaContract` holds an approved provider ID, expected `chatgpt`
authentication mode, exact observed limit IDs, each bucket’s logical purpose,
whether a secondary window is required, and documented reached-type values.
It intentionally has no hardcoded five-hour or weekly duration. Official
subscription information says five-hour and weekly limits may both apply.
Accordingly, this offline contract may return `AVAILABLE` only when its
versioned, source-verified configuration explicitly maps both applicable
logical categories (`five_hour` and `weekly`) to provider limit IDs. A partial
or unverified mapping returns `QUOTA_UNKNOWN`; a future plan-specific exception
requires separate official verification and a new contract version.

`normalize_codex_quota()` separates:

1. **schema validity** — types, percentages, timestamps and uniqueness;
2. **source validity** — source attestation, subscription mode, auth mode,
   plan type, 300-second freshness and legacy/multi-bucket consistency;
3. **quota interpretation** — reached type or `usedPercent >= 100` blocks;
4. **execution authorization** — always false in this module.

Unknown or missing required/secondary buckets, unexpected IDs, invalid percent,
stale/future timestamp, source failure, conflicting legacy bucket, unknown
reached type or API-key mode becomes `QUOTA_UNKNOWN`. Multiple active limits are
preserved in `blocking_limits`; weekly is the primary displayed state if both
are active, without losing the five-hour block.
