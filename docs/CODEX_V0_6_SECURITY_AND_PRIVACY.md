# Codex-first security and privacy feasibility v0.6

## Boundary

Verified on **2026-10-14**. This public repository remains unable to execute a
provider request and must never contain credentials, private tasks, KAYA source,
account identifiers, raw provider output or private-runtime configuration.

## Future private design

| Boundary | Required control |
| --- | --- |
| Project | Separate private OpenAI project for synthetic proof only; no KAYA data or production project. |
| Identity | Least-privilege project service account; no workload owner/admin role. |
| Credential | Prefer short-lived workload-identity token if supported; otherwise scoped, expiring server-side key in an approved secret manager. |
| Controller | Authenticated private app validates allowlists, task digest, approvals, expiry, one-use grant, budget and stop. |
| Provider | Fixed `environment.type: "none"`; no tools/MCP/vault/files; one text-only turn; default-deny egress except approved API endpoint. |
| Output | Private deterministic JSON review; only sanitized status/digests in audit; no automatic writeback. |

OpenAI documents bearer API keys or workload-identity tokens, server-side secret
handling, project-scoped RBAC and service accounts. [Authentication](https://developers.openai.com/api/reference/overview), [RBAC](https://developers.openai.com/api/docs/guides/rbac), [service accounts](https://developers.openai.com/api/docs/guides/terraform/service-accounts)

## Incident and reconciliation requirements

- A durable single-use ExecutionGrant binds task digest, provider/model, scope,
  expiry, request ID, idempotency key and separate provider/paid approval.
- Atomically reserve before provider start and persist the possible-start
  boundary. Timeout, crash, cancellation ambiguity or network error becomes
  `UNKNOWN_PROVIDER_OUTCOME`; it never automatically releases budget.
- Check emergency stop before grant, reservation, provider start, retry and
  result release. A missing or non-explicit false stop blocks. On stop, request
  cancellation where supported and reconcile uncertainty manually.
- Use append-only sanitized audit events, access controls and a retention policy;
  obtain independent security review before live use.

The API documents active-turn cancellation and session deletion, but an idle or
completed turn alone is not a safe application outcome. [Session handling](https://developers.openai.com/api/docs/guides/agents-api/sessions)

## Privacy decision

Only the fixed synthetic JSON artifact may cross the future provider boundary.
No personal, property, private-code, source-control, credential or operational
data is allowed. This is mandatory because the Agents API overview states that
Agents API supports US-only data residency and not Zero Data Retention. General
platform data controls do not override that Agents API limitation.
[Agents overview](https://developers.openai.com/api/docs/guides/agents-api/overview), [data controls](https://developers.openai.com/api/docs/guides/your-data)

| Threat | Control |
| --- | --- |
| Task scope changed | Immutable digest plus exact schema/allowlists. |
| Credential leakage | Server-only secret boundary and redacted audit. |
| Replay or duplicate charge | One-use request/idempotency and durable accounting. |
| Delayed outcome/cost | Unknown state holds budget until reconciliation. |
| Tool or repository access | No environment/tools/MCP/vault/files. |
| Unsafe publication | Local review and separate human release authority. |
