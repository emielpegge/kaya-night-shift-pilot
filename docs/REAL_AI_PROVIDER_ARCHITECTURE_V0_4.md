# Real AI Provider Architecture v0.4

## Purpose and boundary

v0.4 is a design and contract phase only. The public pilot still executes one
fixed synthetic task through the existing MOCK controller, router adapter, and
worker. It contains no provider SDK, HTTP client, provider URL, credential,
environment variable, live execution path, or workflow change. Every request
whose mode is `LIVE` is rejected with `LIVE_PROVIDER_EXECUTION_DISABLED`, even
when a hypothetical policy says live use is enabled.

The v0.4 contracts are deliberately not connected to `controller.py` or
`worker.py`. This preserves the v0.3 chain and prevents a router result from
becoming live execution authority.

## Reused architecture and required additions

| Existing component | Reuse in a future approved version | Additional boundary before live use |
| --- | --- | --- |
| Controller/environment checks | Fixed task, branch, stop, and manual-dispatch gates | Signed authorization and repository-specific policy lookup |
| Router and adapter | Deterministic suitability decision plus audit | Provider choice remains advisory until authorization succeeds |
| Prepared/worker handoffs | Exact-spec and result integrity bindings | Authenticated, expiring execution grant; never a raw secret |
| MOCK worker | Test-only reference behaviour | Separate isolated provider executor, no task-shell execution |
| v0.2 simulation | Synthetic policy evaluation only | Measured, provider-verified rate/cost data under controlled review |
| Workflow | Public safety regression fixture | A separate, private, explicitly approved live workflow only |

## Versioned adapter contracts

`night_shift_pilot.provider_contracts` defines version
`night-shift-provider-contract-v0.4`:

- `ProviderCapability`: provider/model identity, task fit, capacity, declared
  authentication modes, opaque cost unit, timeout, rate-limit description,
  quality statement, and limitations.
- `ProviderExecutionRequest`: bound request/task/repository/provider/model IDs,
  input digest rather than free executable instruction text, execution mode,
  timeout and per-task maximum cost.
- `ProviderExecutionResult`, `ProviderUsage`, and `ProviderError`: result,
  public-safe error, usage, and audit metadata shapes.
- `ExecutionAuthorization`: distinct approvals for provider use and paid calls.
- `ExecutionPolicy`: provider/task/repository allowlists, cost unit and task/
  night caps, timeout and rate limits. A policy has an explicit contract version.

`InertMockProviderAdapter` is the sole implementation. It returns a
deterministic synthetic marker after policy checks and cannot call a provider.
The `ProviderAdapter` protocol is a future seam, not permission to implement a
live adapter.

No contract field grants authority through model output or instruction text.
Future requests must bind a reviewed task artifact and digest; they must not
carry shell commands, arbitrary tool permissions, secrets, or free-form write
rights.

## Codex and Claude: separate future designs

### Codex Provider Adapter

Potential future paths must be separately evaluated, not conflated:

1. A ChatGPT/Codex product subscription and interactive Codex surfaces.
2. The official OpenAI API for application requests.
3. A supported Codex API/Agents integration, if selected and approved.
4. Local CLI or app integrations, which are not interchangeable with API
   billing or server-side authorization.

For an API path, OpenAI documents bearer API credentials or short-lived tokens
from workload identity federation; credentials must be server-side and never in
client code, Git, artifacts, logs, or prompts. OpenAI also documents request-ID
and rate-limit headers for production diagnostics. The design must verify the
selected product surface, model availability, billing project, current limits,
approved scopes, data handling, and exact cost units at implementation time.
No credits, subscription entitlement, free use, model name, or price is assumed
by this repository. See official OpenAI documentation: [API overview](https://developers.openai.com/api/reference/overview)
and [workload identity federation](https://developers.openai.com/api/docs/guides/workload-identity-federation).

### Claude Provider Adapter

Claude integration remains a separate provider decision. A future adapter must
verify through Anthropic's then-current official documentation: the approved API
surface or other officially supported path, authentication method, model IDs,
pricing/billing, rate limits, retry rules, request IDs, data retention, and
tool-execution boundaries. A Claude product subscription, API access, CLI, and
third-party integration must be treated as separate systems until independently
verified. v0.4 includes no Anthropic SDK, URL, credential, or pricing claim.

Both provider adapters must conform to the same local execution authorization
contract, but their billing, limits, identity and provider request metadata must
never be converted or assumed equivalent.

## Future authorization and secret handling

Live use defaults to disabled. A separately approved v0.5 design must require,
in order:

1. An exact task allowlist and immutable task digest.
2. Repository/ref allowlisting and an explicitly reviewed execution policy.
3. A router recommendation, independently checked against a provider capability
   profile.
4. A short-lived, authenticated execution authorization with separate provider
   and paid-call approvals.
5. Task and nightly budget reservations in the provider's own cost unit; reject
   unknown pricing or unavailable capacity.
6. A private executor with egress allowlisting, timeout, concurrency/rate limits,
   request IDs and idempotency keys.

Prefer dedicated provider project/service identities and short-lived federated
workload credentials over long-lived keys. Secrets belong only in an approved
private secret manager or provider-supported federation configuration. They
must never appear in this public repository, GitHub artifacts, logs, prompts,
model context, exception details, container images, or pull-request comments.

## Controlled Codex + Claude cooperation

1. Controller validates a pre-approved task and environment.
2. Router emits an advisory provider/model recommendation and fallback audit.
3. Authorization independently validates stop state, provider/task/repository
   allowlists, capacity, cost, timeout and explicit paid approval.
4. A sandboxed provider executor returns bounded output and sanitized metadata.
5. A separately authorized independent reviewer checks task compliance, tests,
   provenance and safety; it may not merge or publish.
6. Controller records feedback and may request a bounded retry only while all
   budgets, rate limits and approvals remain valid.
7. A human performs any publication, merge, deployment, credential, or billing
   action through a separate approval path.

Provider outage, rate limit, insufficient budget, invalid/partial output,
review failure, contradictory review, repeated error, timeout, or an active
emergency stop produces `NO_EXECUTION`/blocked state. No automatic fallback may
weaken the task, cost, repository, review, or approval policy.

## Audit, review and attack resistance

Record only public-safe, minimised metadata: policy/contract versions, task and
input digests, selected provider/model IDs, authorization reference digest,
timestamps, timeout/rate/budget decisions, provider request ID when safe, and
sanitized outcome/review codes. Never record tokens, prompts containing secrets,
raw credentials, private source, or unrestricted model output in public logs.

Key attack scenarios and controls:

- Forged router choice or handoff: reconstruct deterministic decisions and bind
  authenticated, expiring grants in a future private environment.
- Prompt injection/tool escalation: fixed task artifacts, no arbitrary tool or
  shell capability, egress and filesystem sandboxing.
- Billing abuse: default-disabled live path, separate paid approval, reservations
  and per-task/nightly caps.
- Cross-repository abuse: exact repository/ref allowlists and workload identity
  claim binding.
- Provider outage/retry storm: bounded retry policy, idempotency and rate limits.
- Malicious output/publication: independent review and human-only merge,
  deployment, scheduling, credential and payment actions.

## v0.5 entry criteria

A new, private, separately approved v0.5 proposal must identify one specific
provider path and model, obtain current official provider evidence, establish
private credential/federation and audit storage, define a bounded task and tool
sandbox, test authorization/budget/rate/stop failure modes, and require an
independent security review. It must not reuse this public pilot's workflow for
live credentials or execution.
