# Codex subscription-only financial feasibility v0.6

## Selected operational policy

KAYA may use only existing included subscription allowance. The operational
budget for additional provider usage is therefore **zero**. The following paths
are explicitly prohibited: API billing, pay-as-you-go, usage credits, purchased
or banked resets, plan upgrades, quota-reset purchases, another account and
automatic fallback that creates extra cost.

This means no token-to-currency estimate can represent the cost of included
subscription tasks: official documentation says that API token prices are
separate from subscription usage and must not be used to estimate included
tasks. Availability and allowance depend on plan, model, task and settings;
the usage dashboard is the authoritative account-specific view.
[ChatGPT pricing](https://learn.chatgpt.com/docs/pricing)

## Capacity policy

| Condition | Financial decision |
| --- | --- |
| Fresh official quota evidence and manual authorization | `AVAILABLE`; a manually initiated subscription task may be considered. |
| Five-hour/weekly limit reached | No new task or cost path; checkpoint and `WAITING_FOR_RESET`. |
| Missing, stale or malformed quota evidence | `QUOTA_UNKNOWN`; no work. |
| Credits, paid reset, API billing, upgrade or automatic paid fallback available | `MANUAL_REVIEW_REQUIRED`; do not use it. |
| Reset timestamp reached | No automatic resume; take a fresh quota read and obtain fresh authorization. |

The policy module treats any cost-bearing option as a violation rather than a
fallback. It has no billing API, account access, purchase, reset or resume code.

## Non-selected API-billing alternative

The prior `gpt-5.3-codex` API calculation is retained only as a rejected design
comparison, not as KAYA's operational cost model. It must not be used to justify
an API call or infer subscription capacity. The previously verified official
standard rates were USD 1.75 / 1M input and USD 14.00 / 1M output tokens on
2026-10-14. [API pricing](https://developers.openai.com/api/docs/pricing)

| Tasks | Low API estimate | Expected API estimate | High API estimate |
| ---: | ---: | ---: | ---: |
| 1 | $0.00525 | $0.02100 | $0.06300 |
| 10 | $0.05250 | $0.21000 | $0.63000 |
| 100 | $0.52500 | $2.10000 | $6.30000 |
| 1,000 | $5.25000 | $21.00000 | $63.00000 |

These figures are deliberately excluded from subscription-only approval,
capacity and accounting decisions. `codex_feasibility.py` remains a pure offline
comparison calculator and makes no request.

## Consequence

The only safe current operational mode is **manual, subscription-bound and
checkpointed**. Unmanaged nightly execution remains financial NO-GO until an
officially supported, secure, subscription-only automation route can prove
quota state and prohibit every paid continuation path.
