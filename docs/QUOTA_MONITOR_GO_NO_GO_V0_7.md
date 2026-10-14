# Quota monitor v0.7 Go/No-Go

## Current result: NO-GO for a live read-only connector

The offline design and tests are ready; no live connector is authorized. A
future read-only quota integration remains NO-GO until every gate is proven and
approved:

| Gate | Current status | Requirement |
| --- | --- | --- |
| Official protocol | Documented and rechecked 2026-10-14. | Pin compatible local client/protocol version. |
| Supported deployment use | Hosted/commercial App Server auth restriction documented. | Confirm the proposed local use case is permitted by OpenAI. |
| Authentication | No token is present or designed here. | Human-approved local ChatGPT subscription auth, MFA and secure OS storage; no API key. |
| Exact bucket mapping | Generic contract only. | Capture approved official account schema without publishing account data; configure all required IDs/secondary rules/reached types. |
| Trusted origin | Synthetic flag only. | Connector cryptographically/process-bound source and anti-replay design reviewed. |
| Read-only enforcement | Offline allowlist tested. | Connector proves no forbidden method, model call, billing action or task execution is reachable. |
| Recheck | Offline plan only. | Separate approval for a local read-only timer/process; no task auto-start. |
| Privacy | Synthetic/public design only. | No account data or KAYA data in logs; privacy/security review complete. |

Even after a future GO for read-only quota inspection, automatic model work and
automatic task resumption remain separate NO-GO decisions. `NIGHT_SHIFT_STOP`,
human authorization and all subscription-only rules remain binding.
