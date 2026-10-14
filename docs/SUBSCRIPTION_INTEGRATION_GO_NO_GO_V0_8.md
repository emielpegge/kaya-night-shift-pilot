# Subscription integration v0.8 Go/No-Go

## Answer to the v0.8 question

**NO-GO.** Official documentation proves that local ChatGPT-sign-in clients
exist, but it does not prove that KAYA Night Shift may independently develop,
stop, and restart after reset under a subscription with a hard zero-credit
guarantee and the required hosted/commercial rights.

## Scenario decisions

| Scenario | Decision | Why |
| --- | --- | --- |
| A. Local, manually supervised development | `CONDITIONAL_GO` outside Night Shift | Official local desktop/CLI ChatGPT sign-in is documented. A person must separately verify plan/workspace eligibility, permissions, allowed data, cost controls, and review every consequential action. |
| B. Local, unattended night development | `NO-GO` | No approved KAYA automation route, no proved credit-exclusion invariant, and no approved authentication/secret/runtime design. |
| C. Hosted/commercial KAYA Night Shift | `NO-GO` | App Server authentication is explicitly prohibited for commercial/hosted services; SIWC eligibility for paid/remotely hosted apps is not established here. |
| D. Read-only quota inspection | `NO-GO` for live use | v0.7 has only offline contracts. A future local connector requires approval, trusted source binding, exact current bucket mapping, and route-permission confirmation. |
| E. Automatic resumption after reset | `NO-GO` | v0.7 can only model a recheck and candidate. Fresh quota cannot override emergency stop or replace a new human authorization. |

`CONDITIONAL_GO` is not permission to run this repository's controller, worker,
workflow, or any unattended process. It is a limited statement about a person
using a supported local Codex client outside this design-only pilot.

## Required evidence before reconsideration

1. Written, current OpenAI confirmation that the exact KAYA use case and
   execution placement are permitted by the selected subscription route.
2. A route-specific, independently validated proof that credits, resets,
   upgrades, API billing, and alternate-account fallback cannot occur.
3. A human-approved local security design covering account authentication,
   credential storage, MFA, device trust, logs, data classification, and
   incident response.
4. An approved read-only quota connector that passes v0.7's trusted-source,
   complete-bucket, freshness, and fail-closed gates.
5. A separate authorization design for one synthetic task. It must maintain
   `NIGHT_SHIFT_STOP`, prohibit automatic resume, and have no deployment,
   merge, or publication capability.
6. Independent legal/security review of provider terms, workspace controls, and
   the proposed commercial/hosted boundary.

The sources for this conclusion are the official [authentication](https://learn.chatgpt.com/docs/auth),
[App Server](https://learn.chatgpt.com/docs/app-server),
[Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt), and
[SIWC overview](https://developers.openai.com/siwc/token-sharing-open-source)
documentation, rechecked on 2026-10-14.
