# Local Codex development options v0.9

Official OpenAI documentation was reviewed on **2026-10-14**. v0.9 is research,
design, and offline simulation only. No Codex/Claude login, local client,
credential, quota request, model turn, scheduler, or provider call was made.

## Local options

`SUPPORTED` below means a technical client path is documented. It does not
establish that a KAYA scenario has a right to use it, nor that it meets KAYA's
zero-additional-cost policy.

| Option | Official technical basis | Authentication/use boundary | Quota and checkpointing | Cost result | v0.9 decision |
| --- | --- | --- | --- | --- | --- |
| A. Human-guided Codex CLI | [CLI](https://learn.chatgpt.com/docs/cli) and [authentication](https://learn.chatgpt.com/docs/auth) document local ChatGPT sign-in | Person signs in through the official browser flow; workspace eligibility and permissions are account-specific | Dashboard/reset information is account-specific; v0.7 remains offline only | API-key mode is forbidden; a hard no-credit proof for this exact route is not established | `CONDITIONAL_GO` only for a human using the official local client outside Night Shift |
| B. Human-guided Codex desktop app | [Authentication](https://learn.chatgpt.com/docs/auth) documents ChatGPT sign-in for local desktop work | Local permission profiles and workspace controls apply | A user can inspect visible product status; no KAYA quota connector is approved | Same unresolved no-credit proof | `CONDITIONAL_GO` only outside Night Shift |
| C. Local workflow with manually approved tasks | A local worktree/sandbox design is compatible with documented CLI/desktop local work | Every task requires a new human decision and a single isolated feature branch | Existing v0.6/v0.7 contracts can model checkpoint/recovery but cannot operate a client | No programmatic price or credit assurance | `CONDITIONAL_GO` as a design, not an implementation |
| D. Future local controller with read-only quota monitoring | App Server documents account/rate-limit surfaces, but v0.7 implements no connector | Requires a separately approved local authentication path and trusted source binding | v0.7 validates complete/fresh evidence and can only plan a conceptual recheck | Credit exclusion and exact account eligibility unproven | `NO-GO` for live use |
| E. Future unattended local execution | [`codex exec`](https://learn.chatgpt.com/docs/non-interactive-mode) is technically documented for scripts/CI/scheduled jobs | Non-interactive access tokens are documented for Business/Enterprise trusted local workflows, not established for this existing subscription | Machine-readable output can record events, but it is not an authorization or quota monitor | No proven hard boundary prevents paid credit use; service accounts are pay-as-you-go | `NO-GO` |

## Technical possibility is not a use authorization

The [non-interactive-mode guide](https://learn.chatgpt.com/docs/non-interactive-mode)
documents `codex exec`, explicit sandbox settings, and scheduled-job technical
uses. The [access-token guide](https://learn.chatgpt.com/docs/enterprise/access-tokens)
documents trusted non-interactive local workflows only for Business and
Enterprise workspaces. Neither source proves that an individual KAYA
subscription is eligible for unattended work, that KAYA may use it for a
commercial platform, or that the run can never use credits.

The [pricing guide](https://learn.chatgpt.com/docs/pricing) says local and cloud
usage share a plan allowance, weekly limits can also apply, and current limits
and reset times are account-specific. It also distinguishes included usage from
paid credits for speed modes. KAYA must not infer an account's entitlements,
limits, reset behavior, or zero-credit state from generic documentation.

## Claude

No Claude client, login, entitlement, quota schema, reset behavior, or terms
are assumed here. Claude remains `QUOTA_UNKNOWN` until an equivalent official,
provider-specific review is independently approved.
