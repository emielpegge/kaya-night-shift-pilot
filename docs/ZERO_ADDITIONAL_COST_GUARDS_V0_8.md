# Zero additional cost guards v0.8

KAYA's additional-AI-cost budget is permanently **zero**. The policy applies
even when a user already has a subscription, a credit balance, or a visible
provider button suggesting a paid continuation.

## Denied actions

The following are denied unconditionally:

- Platform API keys, API billing, and pay-as-you-go;
- purchasing, consuming, banking, or auto-reloading credits;
- activating an earned/banked or paid rate-limit reset;
- subscription upgrades or paid quota changes;
- another account, provider, or billing mode used to bypass a limit;
- model calls merely to test capacity;
- a provider fallback with a different or potentially chargeable cost basis.

The existing v0.6/v0.7 offline contracts retain these denials. No v0.8 code
relaxes them.

## Why connected-app plan usage is not yet sufficient

The official [Sign in with ChatGPT guide](https://learn.chatgpt.com/docs/sign-in-with-chatgpt)
states that app usage counts against the existing plan, but it also documents a
setting to allow connected apps to use credits after a usage limit. The
[SIWC cookbook](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)
likewise describes eligible requests as using plan allowance **or available
credits**.

Therefore this public, offline project has no proven way to establish both:

1. credits cannot be used for the proposed route; and
2. the account's credit-fallback state is authoritatively checked immediately
   before every future execution.

An absent API key is necessary but not sufficient. Until an officially supported
and independently reviewed hard guard satisfies both conditions, all unattended
real execution remains NO-GO.

## Future guard checklist

Any future proposal must prove, not merely configure:

| Guard | Required proof |
| --- | --- |
| Authentication | ChatGPT-plan-only mode; API key and alternative provider modes impossible at the executor boundary. |
| Credit exclusion | Official route-specific control prevents all credit use and its applied state is independently verified. |
| Reset exclusion | Read/write method allowlist denies every reset/credit method; no UI or automation path can invoke one. |
| Cost evidence | No unknown cost component, price fallback, or provider usage mode is accepted. |
| Failure behavior | Missing, stale, contradictory, or unavailable evidence blocks before a task starts. |
| Audit | Sanitized records prove the policy decision without storing account IDs, tokens, plan payloads, or private work. |

These are future acceptance conditions, not functionality implemented by v0.8.
