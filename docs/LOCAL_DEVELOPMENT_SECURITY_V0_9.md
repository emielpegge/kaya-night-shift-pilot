# Local development security v0.9

## Minimum future manual-workflow boundary

For a later, separately approved manual local task, use one synthetic task in
one dedicated feature worktree. Keep main read-only to the task, prohibit
automatic merge/deployment/workflow dispatch, and require human review before
any publication. Do not grant access to another repository, external connector,
MCP server, browser, cloud environment, or additional writable directory.

The [CLI safety reference](https://learn.chatgpt.com/docs/cli/reference)
recommends `workspace-write` for unattended local work that stays inside its
workspace and warns against bypassing sandbox/approval controls. The future
manual design is stricter: no danger-full-access, no approval bypass, no
automatic task, and no live KAYA source.

## Authentication and privacy

The [authentication guide](https://learn.chatgpt.com/docs/auth) documents
ChatGPT sign-in for subscription access and distinct API-key usage-based access.
It also documents credential-storage choices, including OS keyring and
ephemeral storage. v0.9 configures neither: a future manual trial would require
MFA, OS-keyring availability, a trusted device, redacted logs, explicit data
classification, and a new review. No credential may enter this repository,
GitHub Actions, a shell history, artifact, issue, or report.

## Explicitly excluded paths

- API-key login, access-token creation, service accounts, and workload identity;
- remote/hosted App Server, websocket tunnel, cloud environment, or CI runner;
- browser automation, session-cookie extraction, undocumented endpoints, or
  alternate accounts;
- direct modifications to main, automatic PR/merge/deployment, or workflow run;
- real KAYA data, source code, repository access, or provider result.

Service accounts are documented as pay-as-you-go in the official
[service-account guide](https://learn.chatgpt.com/docs/enterprise/service-accounts)
and are categorically incompatible with KAYA's zero-additional-cost policy.

## Human controls

The emergency stop remains the first control. It must be checked before any
future authorization, provider start, retry, publication, or recovery. A
human must separately approve task scope, branch, data classification,
permissions, cost conditions, start, review, and any continuation. A human
pause or emergency stop cannot be lifted by a quota reset or notification.
