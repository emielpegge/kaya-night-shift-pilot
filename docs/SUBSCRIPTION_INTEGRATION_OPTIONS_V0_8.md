# Subscription integration options v0.8

Verified against official OpenAI documentation on **2026-10-14**. This is
research only: no account, token, client, App Server, quota payload, inference
request, or model execution was used.

## Route comparison

`SUPPORTED` means that the documented route exists for the stated local use.
It is not an authorization for KAYA Night Shift. `UNVERIFIED` is a mandatory
NO-GO for the stated scenario. The verdicts do not infer product terms that the
sources do not state.

| Route | Subscription route officially documented | Personal local development | Internal business development | Commercial/hosted KAYA service | Unattended night work | Read-only quota surface | Verdict for v0.8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Codex desktop app + ChatGPT sign-in | Yes, for local work | Supported when available for the account/plan | Supported only for an eligible workspace with its administrator's local-access controls | Unverified: not an embedding/integration entitlement | Unverified | No documented independent quota API in this client route | `SUPPORTED` for manually supervised local use only; all automated/hosted uses `UNVERIFIED` |
| Codex CLI + ChatGPT login | Yes, for local work | Supported | Supported only with applicable workspace access/permissions | Unverified: not an embedding/integration entitlement | Unverified under the zero-additional-cost policy | App Server is a separate surface | `SUPPORTED` for manually supervised local use only; all automated/hosted uses `UNVERIFIED` |
| Local Codex App Server authentication | Documented for local/open-source clients | Supported route exists, subject to account eligibility | Account/workspace dependent | Explicitly prohibited for commercial or hosted services | No-GO for KAYA until the permitted local use is independently approved | `account/read`, `account/rateLimits/read`, and a rate-limit notification are documented | `UNVERIFIED` for KAYA; `PROHIBITED` if commercial/hosted |
| Sign in with ChatGPT (SIWC) | Yes, for eligible plan usage | Supported for open-source/local use, subject to consent | Selected private apps are mentioned, but KAYA eligibility is not proven | Paid/remotely hosted apps must request access; identity-only commercial availability is selective | Unverified | No documented read-only quota contract was established in this review | `UNVERIFIED` for KAYA |
| Codex access tokens | Documented for Business/Enterprise trusted local automation | Not established for personal subscriptions | Supported only for eligible Business/Enterprise workspace administration | Does not itself authorize a hosted commercial service | Could support trusted local automation, but violates v0.8's no-credential scope and has no proved zero-credit guard | Not assessed as a quota-only route | `UNVERIFIED` / out of scope |

## Sources and boundaries

The [authentication guide](https://learn.chatgpt.com/docs/auth) distinguishes
ChatGPT sign-in for subscription access from API-key usage-based access, and
documents desktop app, CLI, and IDE sign-in for local work. API keys are
explicitly excluded from KAYA's policy.

The [Codex CLI guide](https://learn.chatgpt.com/docs/cli) documents local
repository work and ChatGPT login. The [desktop local-environment guide](https://learn.chatgpt.com/docs/environments/local-environment)
describes local worktrees and integrated-terminal actions; it is not a grant for
unattended service operation.

The [App Server guide](https://learn.chatgpt.com/docs/app-server) says that
App Server authentication has never been permitted for commercial or hosted
services. Therefore a hosted KAYA controller must not use it as a workaround.

The [SIWC overview](https://developers.openai.com/siwc/token-sharing-open-source)
states that ChatGPT-plan usage documentation is for open-source and locally
hosted apps, and directs paid or remotely hosted apps to an interest form. This
does not establish eligibility for KAYA.

## Recommendation

The only route with an evidence-backed *local* starting point is a manually
supervised Codex desktop or CLI session using ChatGPT sign-in, after a separate
human check of plan, workspace permissions, terms, and local permission profile.
It must remain outside Night Shift automation. No route in this review is a
GO for a hosted controller, unattended work, or automatic resume.

Claude has no adapter or assumed endpoint in v0.8. It remains `QUOTA_UNKNOWN`
until equivalent official subscription, cost, and automation evidence is
reviewed.
