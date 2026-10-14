# Codex subscription-only security and privacy feasibility v0.6

## Boundary

Verified on **2026-10-14**. This public pilot may not execute an AI task,
authenticate to a provider, retain an account token, query account quota, or
start a workflow. It must never contain private source, KAYA data, credentials,
account identifiers, raw model output or subscription telemetry.

The subscription-only policy prohibits API keys and API billing. Official
documentation distinguishes account-plan usage from API-key usage, which is
billed separately. [ChatGPT pricing](https://learn.chatgpt.com/docs/pricing)

## Future manual-only boundary

| Boundary | Required control |
| --- | --- |
| Identity | A human signs into an official Codex subscription client; no shared, delegated or alternate-account workaround. |
| Capacity | Before a task, the human checks the official usage surface. The controller receives only an approved, sanitized capacity statement, never account authentication. |
| Task | Immutable fully synthetic artifact; no KAYA data, repository, shell, web, MCP, files or tool access. |
| Policy | API billing, credits, paid reset, upgrade and automatic paid fallback are all hard blocks. |
| Start | Explicit human authorization is required after capacity confirmation; no scheduler or background retry. |
| Pause | On a limit, unknown quota or incident: checkpoint, stop new work and request manual review. |
| Output | Deterministic local review, no automatic publication, merge, deployment or follow-up task. |

`subscription_policy.py` is an inert offline representation of those controls.
It does not authenticate, read a quota, execute, resume, buy capacity or contact
Codex/Claude. The Codex App Server documentation is not treated as authorization
for unattended KAYA use even though it documents authenticated quota information.
[App Server](https://learn.chatgpt.com/docs/app-server)

## Incident handling

- Emergency stop remains checked before any future local handoff; missing or
  non-explicit false state blocks.
- `LIMIT_REACHED_5H`, `LIMIT_REACHED_WEEKLY`, `QUOTA_UNKNOWN`, `PAUSED` and
  `MANUAL_REVIEW_REQUIRED` prohibit new model work.
- `WAITING_FOR_RESET` is not a timer-triggered resume. After a displayed reset
  time, a human takes a new quota reading and separately authorizes the task.
- Any prompt to buy credits, use an API key, reset, upgrade, switch account or
  use a paid fallback is a policy violation, not a recovery action.
- Preserve only a local synthetic checkpoint and sanitized audit result. No
  account screen or quota payload is copied to the public repository.

## Privacy

The selected first task is synthetic. No personal data, property data, private
code or operational information can enter a subscription client. This avoids
making unverified data-residency, retention or enterprise-policy claims for a
personal subscription surface. Before any non-synthetic use, privacy, retention,
data-residency and provider terms need an independent review; until then, KAYA
content is excluded.

The future generic Claude policy uses the same default: it is `QUOTA_UNKNOWN`
until official subscription access, quota visibility, privacy terms and explicit
manual controls are verified. No Claude integration is introduced here.
