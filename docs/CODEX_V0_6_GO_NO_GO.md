# Codex-first v0.6 Go/No-Go

## Current result: NO-GO

v0.6 creates a synthetic proof design only. It does not authorize a provider
request. Every gate needs independent verification and separate human approval;
any missing, stale, conflicting or unverified gate remains **NO-GO**.

| Gate | Current evidence | Required for GO |
| --- | --- | --- |
| Integration path | Managed Agents API/no-environment documentation verified. | Recheck current official documentation and product status. |
| Model | `gpt-5.3-codex` has official pricing. | Verify model access in the chosen Agents API project. |
| Project/identity | Scoped RBAC and service-account docs exist. | Private project and proven least-privilege non-owner identity. |
| Financial limits | Offline low/expected/high estimates exist. | Approved exact task/model caps and rechecked price/project limits. |
| Private runtime | Paper design only. | Reviewed controller, secret boundary, default-deny egress and no public linkage. |
| Grants/accounting | Inert local contracts exist. | Authenticated grant, atomic durable reservation/reconciliation and replay controls. |
| Emergency stop | Mock stop and live denial exist. | Private stop/cancellation/unknown-outcome drills pass. |
| Privacy | Synthetic-only scope defined. | Explicit approval of US-only/no-ZDR implication; no KAYA data. |
| Security review | Not performed. | Independent sign-off on implementation, logging, retention and incidents. |
| Specific paid test | Fixed JSON validator proposed. | Human approves digest, 30-second deadline, one turn, no tools and no auto-retry. |

## Required future record

The private controller records approval references, contract/policy versions,
task digest, provider/model, grant/request/idempotency IDs, stop state, budget
reservation, private session ID, terminal state, sanitized usage, deterministic
review, deletion request, reconciliation and human closeout. This public
repository stores none of the private identifiers or raw content.

## Stop criteria

Stop before provider start if any gate is not GO. Stop and contain after start
on required action, unexpected tool/connector event, model mismatch, malformed
output, timeout, cancellation ambiguity, missing usage, pricing change, budget
inconsistency, security alert or emergency stop. Mark uncertain outcome unknown;
do not retry, release budget, publish, merge or run another task without new
human approval.
