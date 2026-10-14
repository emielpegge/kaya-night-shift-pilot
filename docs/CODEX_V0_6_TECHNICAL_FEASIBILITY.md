# Codex subscription-only technical feasibility v0.6

## Decision

Verified on **2026-10-14**. KAYA's selected policy is **subscription-only**:
use only an already included Codex/ChatGPT allowance. API keys, API billing,
pay-as-you-go, purchased credits, paid resets, upgrades, other accounts and
cost-increasing automatic fallback are prohibited.

Codex is officially available through ChatGPT-plan clients such as the desktop
app, Codex CLI, IDE extension and web, subject to plan, rollout and workspace
settings. This is separate from API-key usage, which uses API pricing.
[ChatGPT pricing](https://learn.chatgpt.com/docs/pricing)

**Current result: NO-GO for unmanaged Night Shift execution.** The official
material documents account-bound quota surfaces, but does not establish a
safe, independently verifiable, unattended controller integration for this
public pilot. Only a later, separately approved, manually supervised local
Codex client path may be considered. No provider is integrated by v0.6.

## Official evidence and limits

| Topic | Status | Evidence or implication |
| --- | --- | --- |
| Subscription versus API | Confirmed distinct | API token prices must not estimate included subscription work. [Pricing](https://learn.chatgpt.com/docs/pricing) |
| Supported subscription clients | Confirmed | Desktop, CLI, IDE extension and web availability varies by plan/rollout. [Pricing](https://learn.chatgpt.com/docs/pricing) |
| Quota visibility | Confirmed account-bound | Usage dashboard and active CLI `/status` are documented. [Pricing](https://learn.chatgpt.com/docs/pricing) |
| Quota shape | Confirmed variable | Five-hour and weekly windows may apply; task/model/plan affect consumption. Fixed message counts are not reliable. [Pricing](https://learn.chatgpt.com/docs/pricing) |
| App Server quota events | Confirmed interface, not approved integration | It documents rate-limit reads/updates and reset timestamps, but requires authenticated Codex services and has not been security-reviewed for unattended KAYA control. [App Server](https://learn.chatgpt.com/docs/app-server) |
| Unmanaged subscription automation | Not verified | Therefore blocked rather than inferred. |
| Claude subscription automation | Not investigated or integrated | The same generic policy applies; no provider-specific claim is made. |

## Required capacity states

The pure offline `subscription_policy.py` represents only these states:

| State | Required behavior |
| --- | --- |
| `AVAILABLE` | A trusted provider capacity statement no older than the policy's 300-second TTL and explicit manual start authorization are both present. |
| `LIMIT_REACHED_5H` / `LIMIT_REACHED_WEEKLY` | Start no work; checkpoint and report `WAITING_FOR_RESET`. |
| `QUOTA_UNKNOWN` | Start no work; require human review. |
| `PAUSED` | Start no work; retain checkpoint. |
| `WAITING_FOR_RESET` | Informational follow-up state only; never auto-resumes. |
| `MANUAL_REVIEW_REQUIRED` | Resolve quota, policy or authorization evidence before any new task. |

At reset time, the controller must not resume from a clock calculation. It needs
a new reliable capacity read and a new valid human authorization. Any visible
credit, reset, upgrade, API or fallback path is a policy violation and blocks.

## First practice task, if manually approved later

The fixed synthetic task remains a JSON validator with no KAYA data, repository,
file, shell, web, MCP, tool or follow-up task. It checks exactly three known
inconsistencies and returns a deterministic JSON object. Its immutable input,
expected result, 30-second maximum duration and local deterministic review are
recorded in the prior design history. It is not scheduled, submitted or run by
this branch.

For future Claude subscription access, use the identical default-deny contract:
provider-specific official quota evidence, subscription-only confirmation,
explicit manual authorization, checkpoint on any limit/unknown result, and no
automatic fallback. Until those are independently documented, its state is
`QUOTA_UNKNOWN` and execution is NO-GO.
