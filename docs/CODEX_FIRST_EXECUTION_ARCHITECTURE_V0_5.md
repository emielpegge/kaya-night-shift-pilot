# Codex-first private execution architecture v0.5

## Decision

v0.5 recommends exactly one route for a later, separately approved, first
private proof: **OpenAI Agents API with the managed Codex harness and
`environment: none`**. This deliberately supports only a bounded synthetic,
no-files, no-shell, no-tools task in a separate private control application.
It is not enabled by this repository.

The Agents API is the official route when OpenAI manages the Codex harness and
session state. The official architecture states that an environment is optional;
with no environment, built-in Bash, apply-patch, workspace files and executor
tools are unavailable. That gives the first private proof the smallest execution
surface. [Agents overview](https://developers.openai.com/api/docs/guides/agents)
and [Agents architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)
were verified on 2026-10-14.

No specific model is selected in v0.5. Model availability, entitlement, price,
rate limit, terms, regional availability and the current Agents API status must
be re-verified from official OpenAI documentation and the intended account at
the approval point.

## Existing controls and gaps

The public pilot already has exact fixed-task reconstruction, a manual/main-only
mock workflow, read-only permissions, exact emergency-stop semantics, a
deterministic mock router, immutable handoff checks, and default-denied v0.4
provider contracts. Those contracts are reusable as policy vocabulary only.

They do **not** provide live authentication, a private executor, authenticated
grants, durable accounting, provider billing reconciliation, cancellation,
secret storage, a sandbox, a reviewer, or release authority. Mock success is
not evidence of live safety. The public pilot must never receive provider
credentials, private source, private results, a live task queue, a deployment
role, or write access to any repository.

## Private data flow and trust boundaries

```text
Human approval -> private controller -> grant/accounting store -> Agents API
                                      |                         |
                                      v                         v
                              immutable audit store       managed harness
                                      ^                         |
                                      |                  bounded result
                                      +---- private reviewer ---+
```

The public pilot may publish only generic contract versions and synthetic test
evidence. The later private controller receives approval references, verifies
task/repository/ref allowlists, creates a short-lived authenticated grant, and
keeps secrets and raw outputs in private systems. The initial proof has no
repository checkout and no KAYA production data. It may communicate a
sanitised status and digests to a public audit demonstration only after human
review; it must never transfer secrets, prompts, private output or access tokens.

## ExecutionGrant

The inert `ExecutionGrant` binds task ID, immutable task SHA-256, provider and
model ID, repository/ref, contract/policy versions, independent provider and
paid approvals, cost ceiling, duration, issued/expiry times, request ID,
idempotency key, and human approval reference. A router result is not a grant.

v0.5 only validates local dataclasses. A future private implementation must
issue an authenticated, signed or server-recorded, single-use grant after a
human approval lookup. It must atomically record the request ID/idempotency key,
check expiry against a trusted clock, and reject replay. No key, signing scheme,
token issuance or authorization flow is implemented here.

## Accounting model

The inert state machine models `RESERVED`, `COMMITTED`,
`UNKNOWN_PROVIDER_OUTCOME`, and `RELEASED_PRE_START`, plus an explicit provider
start boundary: `PRE_START_CONFIRMED`, `START_MAY_HAVE_OCCURRED`, or
`START_CONFIRMED`. A future durable service must atomically record the start
boundary before any provider-start attempt. Only an untouched,
`PRE_START_CONFIRMED` reservation can be released. Once start may have occurred,
release is forbidden even if no result is available.

Nightly blocked budget is cumulative: `COMMITTED` uses its committed amount;
`RESERVED` and `UNKNOWN_PROVIDER_OUTCOME` retain their full reservation; only
`RELEASED_PRE_START` releases budget. Therefore a later reservation cannot spend
past earlier committed work. Provider-reported actual use may commit against the
reservation only after correlation; estimated cost is not final cost.

On timeout, retry uncertainty, or crash after provider start, mark the
reservation unknown and retain it: never automatically release an amount whose
provider cost may still arrive. Unknown/invalid state records and invalid
transitions block. Unknown cost model, price, quota, approval, reservation,
idempotency or accounting state blocks execution.

## Emergency stop and results

The future controller checks the central stop before grant issue, provider start,
every retry, and any result release/publication. Missing or non-exact false state
blocks. Active stop admits no new tasks; running tasks receive explicit
cancellation where the provider supports it, otherwise become
`UNKNOWN_PROVIDER_OUTCOME` pending reconciliation. There is no auto-restart.

A future result contract must bind task/request/provider/model/output digest,
status, test outcome, sanitized usage/error metadata, audit reference and review
status. AI output can never merge, deploy, alter credentials, incur another paid
request, publish private data, or modify a branch. A separately authorized
independent review (potentially a later Claude reviewer) can only recommend a
human decision.

## v0.5 does not

- call OpenAI, instantiate a provider client, load credentials, or set provider
  environment variables;
- create a private runtime/repository, database, sandbox, worker, queue or
  GitHub workflow;
- access `kaya-platform`, production data, a shell, a filesystem workspace or
  any live repository;
- issue grants/tokens, charge a provider, or authorise a live request.

`authorize_live_execution()` always returns `DENIED` even for a locally valid
grant. This is deliberate.

## v0.6 go/no-go

GO requires a separate approval for one specific OpenAI account/project, model
and terms; current official verification; private controller and audited secret
boundary; authenticated single-use grants; durable atomic accounting; default-
deny egress; no-files initial scope; independent security review; tested stop,
timeout, reconciliation and reviewer controls; and a named human owner for
budget and incident response. Any missing item is NO-GO.
