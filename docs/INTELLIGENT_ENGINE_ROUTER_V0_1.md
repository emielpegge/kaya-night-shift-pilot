# Intelligent Engine Router v0.1

This deterministic component uses synthetic profiles and mock tasks only. It does
not invoke AI engines, schedule work, modify a repository, or create pull
requests. Provider names are mock labels, not claims about real capabilities,
prices, subscriptions, credits, availability, or quality.

## Contracts and profiles

A task declares one of: backend, frontend, debugging, research, documentation,
architecture, or review. It also declares complexity (1–3), risk, required
capabilities, minimum quality, a synthetic USD budget, and paid-call approval.

Each profile declares supported work, capabilities, complexity/risk ceilings,
quality, deterministic latency, synthetic capacity, and one billing state:

| Billing state | Pilot meaning |
| --- | --- |
| `mock_no_charge` | No-charge synthetic fixture. |
| `synthetic_paid_mock` | Synthetic charge used only to test budget and approval gates. |
| `unknown` | Cost is not verifiable and the profile is blocked. |

Credits, subscriptions, quotas, and API costs are never converted between
providers. A future real integration must provide independently verified billing
and capacity data; unknown data produces `NO_EXECUTION`.

## Routing matrix

| Task class | Required example capability | Eligible synthetic profile(s) |
| --- | --- | --- |
| Backend / debugging | code, tests | `codex-mock`; paid fixture only with approval |
| Frontend | writing, reasoning | `claude-mock` |
| Research / documentation | research or writing | `claude-mock`, `future-provider-mock` |
| Architecture / review | reasoning or review | `codex-mock`, `claude-mock` |

Profiles are fixtures, not a real-engine benchmark.

## Algorithm and feedback

1. Reject invalid task policy with `NO_EXECUTION`.
2. Evaluate every profile for mock-only mode, task fit, capabilities, complexity,
   risk, quality, feedback quality, capacity, verified synthetic cost, budget,
   and paid approval.
3. Retain every rejection or skip reason in the candidate decision record.
4. Choose the lowest eligible synthetic cost; ties use latency rank then engine
   ID. Other eligible engines form the explicit fallback list.
5. If no profile is eligible, return `NO_EXECUTION`; no fallback is attempted.

Quality/reliability feedback is conservative: it can lower eligibility but cannot
create capabilities or capacity. The router only returns a decision. Existing
`NIGHT_SHIFT_STOP` enforcement and all workflow boundaries remain unchanged.

Invalid task, feedback, billing, cost, capacity, complexity, risk, quality, task
kind, or profile fields fail closed with a traceable policy or candidate reason.
Duplicate engine IDs are ambiguous and block every matching profile; neither
selection nor fallback is allowed for them. Candidate records are sorted by ID,
so equivalent profile sets yield the same audit result regardless of input order.
