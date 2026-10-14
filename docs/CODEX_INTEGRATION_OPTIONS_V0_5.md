# Codex integration options v0.5

Official OpenAI documentation was reviewed on **2026-10-14**. Product access,
model catalogues, pricing, rate limits, terms and availability are account- and
time-dependent and are not asserted by this public repository.

| Path | Hosting/control | First-proof assessment |
| --- | --- | --- |
| Agents API / managed Codex harness | OpenAI runs harness and retains session state; application manages policy and optional environment | **Preferred** with no environment: least custom agent loop and no shell/files |
| Agents SDK | Application owns deployment, tools, storage, approvals; SDK runs agent loop | Viable later, but more private-runtime control-plane responsibility |
| Responses API | Application owns complete orchestration/state/tool loop | Not preferred: greatest bespoke safety/orchestration burden |
| Codex CLI / app-server | Local process/application integration; app-server can support persistent conversations and approvals | Not for first private proof: process/token lifecycle and local execution surface require extra controls |

The official comparison says the Agents API suits long-running work with an
OpenAI-managed Codex harness; the SDK runs in the application; and Responses is
for direct model responses with application-controlled integration. See
[Agents overview](https://developers.openai.com/api/docs/guides/agents).

## Recommended route: Agents API, no environment

For the first future private proof, use a private controller plus the managed
Agents API harness with `environment: none`, one synthetic reviewed task, no
tools, no sandbox, no repository and no external data. Official architecture
states that no environment means no built-in Bash, apply-patch, workspace files
or executor MCPs. [Architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)

This path still requires private API authentication, explicit spend approval,
current model/feature availability, usage/rate-limit verification, cancellation
and audit design. It is a recommendation, not authorization.

## Alternatives and verification items

**Agents SDK.** Useful when a private controller must own tools, storage,
approvals and runtime behavior. Its official guide says the SDK runs in the
application while the server owns those responsibilities. Verify SDK maturity,
language/version, tracing retention, model/provider selection and sandbox
policy. [Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)

**Responses API.** Provides the most direct control but requires building the
agent loop, state/recovery, tool policy and audit controls ourselves. It is not
appropriate before those controls exist.

**Codex CLI/app-server.** Official documentation describes app-server as a
process driven over stdio and, for ChatGPT plan usage, an OAuth token path to
Responses. The model list is not an entitlement check; a successful inference
turn confirms access only for that request. This is distinct from API project
billing and interactive ChatGPT/Codex product use. Do not put a user OAuth token
in a shared/nightly private executor. Verify current supported use, identity,
terms and token lifecycle before considering it. [Codex app-server](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server)

## Authentication, cost and operational facts to re-check

OpenAI’s API overview documents API keys or short-lived workload-federation
tokens, server-side secret handling, request IDs and rate-limit headers. The
federation guide recommends dedicated service accounts, environment separation,
exact claim matching and least privilege. These are future private-boundary
inputs only. [API overview](https://developers.openai.com/api/reference/overview),
[workload identity federation](https://developers.openai.com/api/docs/guides/workload-identity-federation).

ChatGPT subscription, Codex product usage and API billing are separate systems.
No credits, included usage, price, model name, capacity or entitlement is assumed.
