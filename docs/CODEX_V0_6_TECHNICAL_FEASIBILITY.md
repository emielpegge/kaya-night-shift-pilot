# Codex-first technical feasibility v0.6

## Scope and result

This is a research and offline-design record, verified on **2026-10-14**. It
does not create an OpenAI account, project, credential, session, request,
provider client, or network connection. All existing live-execution paths in
this public pilot remain denied.

**Proposed future route:** one separately approved [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview)
session using the OpenAI-managed Codex harness, `environment.type: "none"`,
no configured tools, no remote MCP servers, no skills, no vault IDs, no files,
and no follow-up turn. Without an environment, built-in Bash, apply-patch,
workspace files and executor MCPs are unavailable. [Architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)

The route is technically plausible but **not approved for execution**. Model
availability, Agents API entitlement, account limits and exact request schemas
remain account-dependent checks.

## Evidence status

| Topic | Status | Evidence or required check |
| --- | --- | --- |
| Managed harness and durable sessions | Officially confirmed | [Agents overview](https://developers.openai.com/api/docs/guides/agents-api/overview) |
| No execution environment | Officially confirmed | `environment.type: "none"` needs initial input and has no built-in shell/workspace. [Reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/create) |
| Required session permissions | Officially confirmed | `api.agents.read`, `api.agents.write`, `api.responses.write`. [Quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart) |
| Session states, cancellation and deletion | Officially confirmed | [Sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions), [delete](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/delete) |
| Usage data | Officially confirmed, best-effort | It may be null or later change. [Reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/create) |
| Rate limits/retries | Officially confirmed, values account-dependent | Obey `Retry-After`; do not retry quota/billing errors. [Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) |
| `gpt-5.3-codex` in the intended project | Account-dependent | Verify model entitlement through an approved account check. |
| Exact retention/deletion completion SLA | Not verified | Obtain account/provider confirmation before non-synthetic content. |

## Proposed first paid proof

The immutable synthetic input is:

```json
{"schema_version":"synthetic-validator-v1","records":[{"id":"a","state":"active","priority":1},{"id":"a","state":"archived","priority":2},{"id":"b","state":"active","priority":0}],"required_inconsistencies":["duplicate_id","archived_nonzero_priority","invalid_priority"]}
```

The task asks only for a JSON response of the following exact shape:

```json
{"schema_version":"synthetic-validator-result-v1","findings":["duplicate_id","archived_nonzero_priority","invalid_priority"],"status":"VALIDATED"}
```

Acceptance requires valid JSON; exactly those three lexical findings; no extra
keys; status `VALIDATED`; no tool/action event; one session and turn; and
completion within **30 seconds** of the private controller's monotonic deadline.
Malformed/extra output, timeout, cancellation, missing usage, tool request or
unavailable model fails the proof and does not automatically retry.

The controller binds the task SHA-256 to a single-use ExecutionGrant. A local,
deterministic JSON reviewer compares the response. It records sanitized status
and digests only, requests session deletion after review, and retains the budget
reservation if provider completion or cost is uncertain.

## Operational constraints

```text
human approval -> private controller -> authenticated one-use grant
                                           |
                                  Agents API, no environment/tools
                                           |
                                     structured JSON only
                                           v
                           deterministic local reviewer -> human report
```

No repository, filesystem, shell, web, connector, MCP server, function tool,
skill, follow-up turn, publication, merge or deployment belongs in this proof.
The router remains advisory. `idle` is never treated as success by itself.
