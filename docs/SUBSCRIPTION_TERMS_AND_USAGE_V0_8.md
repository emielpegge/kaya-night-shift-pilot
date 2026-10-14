# Subscription terms and usage boundary v0.8

Official sources were reviewed on **2026-10-14**. This document records only
what those sources establish and deliberately leaves unresolved matters
unresolved.

## Established facts

1. [OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth)
   identifies ChatGPT sign-in as subscription access and API-key sign-in as
   usage-based API access. API-key authentication uses standard API pricing and
   is permanently prohibited by KAYA policy.
2. The same guide documents desktop app, CLI, and IDE ChatGPT sign-in for local
   work. Workspace membership, seat, role, feature availability, region, and
   administrator controls remain account-dependent.
3. [Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt)
   says connected-app use counts toward existing plan limits and does not add a
   separate allowance. It also describes a user setting that can allow apps to
   use credits after a usage limit is reached.
4. [SIWC plan-usage documentation](https://developers.openai.com/siwc/token-sharing-open-source)
   is for open-source and locally hosted apps; paid or remotely hosted apps are
   directed to request access. The current documentation does not grant KAYA a
   hosted or commercial entitlement.
5. [App Server documentation](https://learn.chatgpt.com/docs/app-server) states
   that App Server authentication has never been permitted for commercial or
   hosted services.

## What is not established

The sources reviewed do **not** establish that KAYA may:

- operate a commercially hosted Night Shift under an individual's subscription;
- run unattended local work under the existing subscription without separate
  approval and a supported automation route;
- force all possible subscription routes to exclude existing credits through a
  machine-verifiable contract;
- infer eligibility, quotas, reset time, or permitted automation from an
  account's plan name alone.

Internal development of a commercial product is not automatically the same as
offering a commercial/hosted integration. This review treats that distinction as
an authorization question, not an implementation detail. An eligible managed
workspace may permit local Codex use, but KAYA must still verify its workspace
permissions and obtain its own human approval before any separate future trial.

## Questions requiring written confirmation before a trial

1. Is the named KAYA use case eligible for the chosen Codex ChatGPT-plan route?
2. Is its intended local or hosted execution mode permitted for that route?
3. Can the account/workspace enforce a no-credit fallback for that route, and
   can KAYA verify the setting without an inference request?
4. Which account-level plan, regional availability, workspace controls, and
   product terms apply at the moment of the trial?
5. Does the approved route support the requested quota observation and
   cancellation behavior without a paid or API fallback?

Until each answer is independently verified, Night Shift remains unable to
start, continue, or resume a real provider task.
