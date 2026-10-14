# Local versus hosted architecture v0.8

## Boundary

```text
manual local developer -> official local Codex client -> local repository
                                  |
                                  +-> human review / explicit Git action

public Night Shift pilot -> offline policy and synthetic fixtures only
hosted KAYA controller   -> no subscription integration, no App Server auth
```

The public pilot stores no token, account record, quota payload, KAYA source,
or provider result. It cannot start an App Server, model, scheduler, or
automatic continuation.

## Local paths

The [authentication guide](https://learn.chatgpt.com/docs/auth) documents
ChatGPT sign-in for local desktop/CLI/IDE use, subject to workspace and local
permission controls. The [local-environment guide](https://learn.chatgpt.com/docs/environments/local-environment)
shows that desktop actions and worktrees operate on the developer's computer.
This supports a potential human-supervised local workflow, not a Night Shift
service.

If a future approved local quota connector exists, it must preserve this order:

1. Authenticate through a separately approved official local route.
2. Perform only the v0.7 read-only quota operations.
3. Normalize all required windows with fresh, trusted evidence.
4. Checkpoint on any block, uncertainty, interruption, or possible in-flight
   provider result.
5. Plan at most one conceptual recheck after an official reset timestamp.
6. After a new full read, mark only a resume *candidate*.
7. Require a new human authorization and an inactive emergency stop before a
   distinct execution decision.

Quota availability, resume candidacy, and execution authorization remain three
different decisions. A reset timestamp, notification, or checkpoint never
authorizes execution.

## Hosted/commercial paths

The [App Server guide](https://learn.chatgpt.com/docs/app-server) explicitly
prohibits App Server authentication for commercial or hosted services. The
[SIWC overview](https://developers.openai.com/siwc/token-sharing-open-source)
documents open-source/local hosting and sends paid or remotely hosted apps to an
interest form. Neither route creates permission for a KAYA hosted controller.

Consequently, a hosted controller must not receive, proxy, extract, replay, or
share local subscription credentials. It must not use browser automation,
session cookies, undocumented endpoints, a remote websocket tunnel, or an API
key as a substitute. All such designs are outside scope and NO-GO.

## Race and recovery rules for a future local design

- Bind every checkpoint to task digest, provider, execution attempt, and last
  trusted quota observation.
- Reserve a unique attempt before a provider start; preserve an uncertain
  provider outcome rather than retrying it.
- Treat lost notifications as no evidence: obtain a fresh full read after the
  planned reset, not a time-based inference.
- Deduplicate conceptual rechecks by v0.7's checkpoint/target/attempt digest.
- Preserve emergency stop and human pause over any reported recovery.
- Never use a second account or paid route when one bucket is exhausted.

No component implementing these future actions is added in v0.8.
