# Local threat model: API and Control Center

Date: 2026-11-14. Scope: one user on a Mac, FastAPI bound to `127.0.0.1`.
Network exposure, shared accounts, and a public server require a separate review.

## Assets and boundaries

| Asset | Entry point | Main risk | Current control |
| --- | --- | --- | --- |
| Tasks, notes, project registry, Memory Center | Authenticated `/v1/*` routes | Local process or browser reads or changes user data | API token and explicit app-data paths |
| Integration credentials | Settings and adapters | Credential disclosure | Keyring or restricted fallback, redacted logs |
| CPU, RAM, disk, model runtime | Voice/video uploads and model calls | Resource exhaustion | File-size, request-rate, and media concurrency limits |
| Control Center token | Browser `sessionStorage` | Same-origin script reads token | API key required; no untrusted HTML rendering in current UI |
| Future repository/calendar actions | Agent action queue | Unintended command or write | Not enabled; approval and audit are required before launch |

The API uses the socket peer address for local rate limits and rejects
`X-Forwarded-For`. Launch Uvicorn with `--no-proxy-headers`; otherwise its
default proxy middleware can rewrite the peer address before the app sees it.
If a reverse proxy is introduced, review the proxy trust boundary first.

## Abuse cases and verification

- An unauthenticated local process calls protected routes: expect `401` or
  `503` when required token configuration is absent.
- A client spoofs `X-Forwarded-For`: the rate-limit identity stays the socket
  peer; repeated requests still reach `429`.
- Multiple uploads compete for transcription or analysis: excess requests
  receive `429` and `Retry-After`; completion or failure releases the slot.
- A crafted file claims a supported extension: size and media validation still
  apply; ffmpeg/ffprobe run with fixed executable arguments and timeouts.
- An untrusted note or model response asks for an action: it is data, not an
  approval. Future action jobs must validate target paths, display the exact
  planned effect, and log approval before any mutation.
- A dependency or secret enters a PR: CI reports it. Rotate any real leaked
  credential; removing it from a later commit does not revoke it.

## Remaining release checks

- Verify CI scanners on a PR and review findings before changing pinned packages.
- Verify packaging, backup/restore, permissions, and clean-machine behavior on
  macOS. The unsigned ZIP remains a tester artifact.
- Before remote access, revisit browser token storage, CSP, TLS, proxy trust,
  rate-limit storage across processes, and cross-origin policy.
