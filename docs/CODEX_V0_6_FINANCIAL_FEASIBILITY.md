# Codex-first financial feasibility v0.6

## Status and source

All amounts are offline estimates from the official pricing page, verified on
**2026-10-14**. They are not a quote, invoice, reserved budget, entitlement or
approval to make a request. ChatGPT subscriptions are not API credit.

The candidate model is `gpt-5.3-codex`. The official table lists standard input
at **USD 1.75 / 1M tokens**, cached input at **USD 0.175 / 1M**, and output at
**USD 14.00 / 1M**. The estimates deliberately assume no cache. Regional
processing pricing and applicability are account- and region-dependent.
[Official pricing](https://developers.openai.com/api/docs/pricing)

The proposed proof has no environment, tools, files or containers. It assigns
**USD 0** additional tool/container cost; any unexpected component is NO-GO
until priced and approved. The Agents API says model usage is billed at selected
API rates, with tool/sandbox costs separate. [Agents overview](https://developers.openai.com/api/docs/guides/agents-api/overview)

## Explicit token scenarios

| Scenario | Input/task | Output/task | Input cost/task | Output cost/task | Total/task |
| --- | ---: | ---: | ---: | ---: | ---: |
| Low | 1,000 | 250 | $0.00175 | $0.00350 | $0.00525 |
| Expected | 4,000 | 1,000 | $0.00700 | $0.01400 | $0.02100 |
| High | 12,000 | 3,000 | $0.02100 | $0.04200 | $0.06300 |

| Tasks | Low total | Expected total | High total |
| ---: | ---: | ---: | ---: |
| 1 | $0.00525 | $0.02100 | $0.06300 |
| 10 | $0.05250 | $0.21000 | $0.63000 |
| 100 | $0.52500 | $2.10000 | $6.30000 |
| 1,000 | $5.25000 | $21.00000 | $63.00000 |

Formula: `tasks × ((input_tokens × 1.75) + (output_tokens × 14.00)) / 1,000,000`.
`codex_feasibility.py` implements it with Decimal and rejects malformed or
negative inputs. It performs no I/O.

## Controls required before a paid proof

1. A human approves the exact model, immutable task, high-case task cap and
   cumulative night cap.
2. A private controller atomically reserves budget before provider start.
   Committed, reserved and unknown outcomes all count; only confirmed pre-start
   release frees budget.
3. Session `spend_control` may be a provider-side cap, but does not replace
   controller accounting because reported usage is best-effort and may change.
   [Session reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/create)
4. Reconcile provider usage, request/session IDs and billing status before
   closing a reservation.
5. Unknown pricing, model access, quota, tool charge, usage or billing is
   fail-closed NO-GO.

The calculator does not model caching, regional uplift, rounding, taxes,
discounts, retries or delayed billing. The first proof prohibits auto-retry.
