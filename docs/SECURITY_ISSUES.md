# Security Issues Tracker

Date: 2026-04-27  
Scope: API auth, integrations secrets, logging privacy, dictation API safety

## Closed

### SEC-001: API open when auth token is missing
- Status: closed in `v0.5.21`
- Files:
  - `apps/api/deps.py`
  - `config/settings.py`
- Verification:
  - Set `VASYA_API_REQUIRE_AUTH=true`
  - Keep `VASYA_API_AUTH_TOKEN` empty
  - Request `/v1/chat` => `503 API auth token is not configured`

### SEC-002: WebSocket auth token allowed in query string by default
- Status: closed in `v0.5.21`
- Files:
  - `apps/api/deps.py`
  - `config/settings.py`
- Verification:
  - `VASYA_API_ALLOW_QUERY_TOKEN=false`
  - Connect `ws://.../v1/ws/voice?api_key=...` without header => rejected
  - Connect with `x-api-key` header => accepted

### SEC-003: Integration tokens stored in plain `storage/integrations.json`
- Status: closed in `v0.5.21`
- Files:
  - `services/integration_settings_service.py`
  - `services/secret_store.py`
  - `requirements.txt`
- Verification:
  - Save tokens in settings UI
  - Check `storage/integrations.json`: no `*_token` fields
  - Restart app and verify token-backed integrations still work

### SEC-004: Raw sensitive text in interaction logs
- Status: closed in `v0.5.21`
- Files:
  - `utils/logger.py`
  - `config/settings.py`
- Verification:
  - Use defaults: `LOG_REDACT_SENSITIVE=true`, `LOG_INCLUDE_TEXT_CONTENT=false`
  - Trigger interactions
  - Check `storage/interactions.log`: text fields are redacted and secrets masked

### SEC-005: Dictation API could post to arbitrary host
- Status: closed in `v0.5.21`
- Files:
  - `voice/session.py`
  - `config/settings.py`
- Verification:
  - Set dictation target to API with non-allowlisted host
  - Try dictation => explicit rejection message

## Open

### SEC-006: Missing rate-limit/throttling in API/WS
- Status: open
- Priority: high
- Suggested fix:
  - Add per-IP request window for `/v1/chat` and `/v1/pipeline`
  - Add WS message frequency and concurrent session limits

### SEC-007: Insufficient automated security tests
- Status: open
- Priority: medium
- Suggested fix:
  - Add unit tests for auth modes, WS auth policy, and logger redaction
  - Add migration test for legacy integration tokens
