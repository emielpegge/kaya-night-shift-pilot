# Local subscription Go/No-Go v0.9

## Decisions

| Scenario | Decision | Basis |
| --- | --- | --- |
| Local, human-guided Codex CLI/desktop development | `CONDITIONAL_GO` outside Night Shift | Official local ChatGPT-sign-in clients are documented. Use remains subject to actual plan/workspace eligibility, manual cost inspection, local controls, and human review. |
| Local workflow with one manually approved synthetic task | `CONDITIONAL_GO` as a future design only | Existing offline policies can bind task/checkpoint/review, but no client or credentials are implemented here. |
| Live local read-only quota monitor | `NO-GO` | v0.7 is offline only; trusted source/authentication, account-specific bucket mapping, and route permission are not approved. |
| Local unattended Night Shift | `NO-GO` | Technical `codex exec` support does not prove personal-subscription entitlement, zero-credit guarantee, or KAYA's required authorization/recovery boundaries. |
| Local Business/Enterprise access-token automation | `NO-GO` for KAYA | Officially documented only for eligible workspaces; it needs credentials and independent confirmation of the cost basis. It is outside this phase. |
| Hosted/commercial controller | `NO-GO` | v0.8 findings remain: no approved route and App Server authentication is prohibited for commercial/hosted services. |
| Automatic resume after reset | `NO-GO` | Fresh quota can yield only a candidate; new human authorization and an inactive stop remain required. |

## Zero-additional-cost result

**Not proven for unattended local work.** The official documentation separates
subscription and API authentication, but it does not give this public project a
machine-verifiable invariant that an eligible unattended KAYA run can never
consume credits, select a paid mode, or encounter account-specific billing
behavior. The existing zero-cost policy therefore wins: do not execute.

## Recommended next step

Do not build a connector or scheduler. First obtain written, route-specific
OpenAI confirmation for the intended KAYA local use and its cost boundary, then
have an independent reviewer evaluate a proposed manual-only synthetic trial.
That proposal must keep `NIGHT_SHIFT_STOP`, live denials, a single feature
branch, no real KAYA data, no workflow run, no merge, and no automatic resume.

Claude remains `QUOTA_UNKNOWN` pending separate official local-subscription,
quota, cost, and automation research.

Sources rechecked on 2026-10-14: [authentication](https://learn.chatgpt.com/docs/auth),
[CLI](https://learn.chatgpt.com/docs/cli), [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
[access tokens](https://learn.chatgpt.com/docs/enterprise/access-tokens), and
[pricing](https://learn.chatgpt.com/docs/pricing).
