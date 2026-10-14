# Private execution security v0.5

## Required future boundary

Create a separate private control application/runtime, not a fork of this public
pilot. The first proof uses no `kaya-platform` checkout, no production data and
no private source. It receives only one reviewed synthetic artifact by digest.

The service identity is dedicated, short-lived where supported, and least
privilege. It has no main write permission, no merge/deploy/scheduler/IAM
authority, and no broad GitHub token. Repository and ref are exact allowlists.
The executor has a read-only/minimal filesystem, no host mounts, no shell access
for the first proof, default-deny network, and only separately approved provider
egress in later phases. There is no automatic publication.

## Threat model

| Threat | Required mitigation |
| --- | --- |
| Stolen credential | Private secret manager/federation, short lifetime, rotation, no logs/artifacts/prompts |
| Forged/replayed request | Authenticated single-use grant, trusted clock, durable request/idempotency ledger |
| Budget race or delayed charge | Atomic reserve/commit/reconcile; unknown outcome retains reserve |
| Prompt/tool escalation | Immutable task digest, no free-form tool rights, first proof has no tools/shell/files |
| Cross-repository access | Exact repository/ref claims and no production repository in initial allowlist |
| Stop during execution | Check before every boundary; cancel if supported or mark unknown; no restart |
| Untrusted output | Sanitized result contract, independent review, human-only merge/deploy/publication |

## Audit and incident handling

Keep private, access-controlled records of grant/policy version, task digest,
approval reference, request/idempotency IDs, provider request correlation,
reservation lifecycle, result digest, review state and stop decisions. Never
store raw secrets or unnecessary provider output in the public pilot.

An incident activates the central stop, blocks new grants, records in-flight
tasks as cancelled/unknown, preserves reservations, revokes/restricts identities
under the provider/private-runtime procedure, and requires reconciliation plus
human approval before any new run. No retry or release is automatic when cost or
provider outcome is uncertain.
