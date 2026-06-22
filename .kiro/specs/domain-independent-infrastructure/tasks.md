# Implementation Plan: Domain-Independent Infrastructure

## Overview

This plan implements a domain-independent infrastructure layer where all URL resolution, CORS configuration, authentication redirects, and email configuration are driven exclusively by environment variables. The implementation extends existing files (`config.py`, `main.py`, `supabase.ts`, `axios.ts`) with minimal new modules, enabling domain changes as configuration-only operations with no code modifications.

## Tasks

- [x] 1. Backend — Extend config.py and add URL/CORS helpers
  - [x] 1.1 Extend `app/config.py` Settings class with domain, CORS, and SMTP fields
    - Add `app_domain: str = ""`, `frontend_url: str = "http://localhost:5173"`, `backend_url: str = "http://localhost:8000"`
    - Change `allowed_origins` type from `list[str]` to `str` (comma-separated, parsed at startup)
    - Add SMTP fields: `smtp_host: str = ""`, `smtp_port: int = 587`, `smtp_username: str = ""`, `smtp_password: str = ""`, `smtp_sender_email: str = ""`, `smtp_sender_name: str = ""`
    - Add helper methods: `get_resolved_frontend_url()`, `get_resolved_backend_url()`, `get_parsed_origins()`, `get_smtp_enabled()`, `get_domain_mode()`
    - `get_resolved_frontend_url()` / `get_resolved_backend_url()` strip trailing slashes and validate http(s):// prefix
    - `get_parsed_origins()` parses comma-separated origins, trims whitespace, filters invalid entries, auto-includes `frontend_url`
    - `get_smtp_enabled()` returns True only when `smtp_host`, `smtp_port`, and `smtp_sender_email` are all present
    - `get_domain_mode()` returns `"custom_domain"`, `"platform_url"`, or `"both"` based on APP_DOMAIN and URL values
    - _Requirements: 1.1, 1.2, 1.5, 1.6, 1.7, 2.3, 4.1, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 1.2 Update `app/main.py` — startup validation, CORS integration, and health check
    - In `lifespan`: validate `frontend_url` and `backend_url` formats (fail on invalid with logged error)
    - In `lifespan`: log warnings for missing optional vars (APP_DOMAIN, FRONTEND_URL, BACKEND_URL)
    - In `lifespan`: log SMTP status (enabled/disabled, which vars are missing)
    - In `lifespan`: log domain mode summary
    - In `lifespan`: log warning if APP_DOMAIN is set but FRONTEND_URL is not
    - Replace `settings.allowed_origins` in CORSMiddleware with `settings.get_parsed_origins()`
    - Enhance `/health` endpoint to return: `app_domain`, `frontend_url`, `backend_url`, `domain_mode` fields
    - _Requirements: 1.8, 1.9, 4.4, 4.6, 5.3, 6.2, 6.3, 7.3, 7.5, 8.5, 9.1_

  - [ ]* 1.3 Write unit tests for config helpers and startup validation (`backend/tests/unit/test_domain_config.py`)
    - Test `get_resolved_frontend_url()` strips trailing slashes and uses fallback when empty
    - Test `get_resolved_backend_url()` strips trailing slashes and uses fallback when empty
    - Test invalid URL format raises ValueError (no http(s):// prefix)
    - Test `get_parsed_origins()` parses comma-separated values, trims whitespace, auto-includes frontend_url, filters invalid entries
    - Test `get_smtp_enabled()` returns False when required SMTP vars missing
    - Test `get_domain_mode()` returns correct mode for each scenario
    - Test health check response includes domain fields
    - _Requirements: 1.1, 1.2, 1.3, 1.8, 4.4, 6.1, 6.3, 6.5, 8.5, 9.1_

- [x] 2. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Backend — Email endpoint guard
  - [ ] 3.1 Add email availability dependency in `app/main.py` or `app/dependencies.py`
    - Create a FastAPI dependency that checks `settings.get_smtp_enabled()`
    - Return HTTP 503 with `{"detail": "Email functionality is unavailable"}` when SMTP is disabled
    - Apply to any email-sending endpoints
    - _Requirements: 4.4, 4.5_

  - [ ]* 3.2 Write unit test for email guard (`backend/tests/unit/test_domain_config.py`)
    - Test 503 returned when SMTP is disabled
    - Test request proceeds when SMTP is enabled
    - _Requirements: 4.5_

- [ ] 4. Frontend — Config, Auth Redirect Builder, and integration
  - [ ] 4.1 Update `frontend/src/shared/lib/supabase.ts` — add auth redirect helpers
    - Add `resolveAppDomain(viteAppDomain, windowOrigin)` function: returns `https://{viteAppDomain}` if valid hostname, else windowOrigin
    - Add `isValidHostname(hostname)` helper (basic RFC 1123 check)
    - Add `buildAuthRedirectUrl(path)` that uses resolved domain + path
    - Add `getEmailVerificationUrl()` and `getPasswordResetUrl()` exports
    - Pass `emailRedirectTo` in signUp, resetPasswordForEmail, and signInWithOtp calls (where used)
    - Log `console.warn` when VITE_APP_DOMAIN is set but invalid
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 9.5, 9.6, 9.7_

  - [ ] 4.2 Update `frontend/src/shared/lib/axios.ts` — use VITE_API_URL with fallback
    - Ensure `baseURL` reads from `import.meta.env.VITE_API_URL` with fallback to `http://localhost:8000/api/v1` (already done, verify no hardcoded custom domains)
    - _Requirements: 2.1_

  - [ ]* 4.3 Write unit tests for auth redirect helpers (`frontend/src/shared/lib/supabase.test.ts`)
    - Test `resolveAppDomain` with valid domain, empty, undefined
    - Test `buildAuthRedirectUrl` produces correct URL without double slashes
    - Test `isValidHostname` with valid and invalid inputs
    - Test fallback used when VITE_APP_DOMAIN is invalid
    - _Requirements: 3.1, 3.2, 3.3, 3.6_

- [ ] 5. Checkpoint — Ensure all frontend and backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Environment documentation and recovery guide
  - [ ] 6.1 Update `backend/.env.example` with all new environment variables
    - Add APP_DOMAIN, FRONTEND_URL, BACKEND_URL, ALLOWED_ORIGINS with format comments
    - Add SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_SENDER_EMAIL, SMTP_SENDER_NAME
    - Document expected formats and defaults
    - _Requirements: 7.1, 7.2_

  - [ ] 6.2 Create `DOMAIN_RECOVERY.md` at project root
    - Document the recovery procedure: update env vars → update Supabase redirect URLs → redeploy
    - List exact variables to change per service (Vercel frontend, Render backend, Supabase dashboard)
    - Include the three domain scenarios: custom domain, platform URLs only, mixed
    - Note that original Vercel/Render URLs always continue working
    - _Requirements: 7.1, 7.2, 7.4, 8.3, 8.4, 8.6_

- [ ] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Basic unit tests are sufficient — no property-based testing needed for MVP
- Implementation extends existing files (config.py, main.py, supabase.ts, axios.ts) rather than creating multiple abstraction layers
- Backend uses Python (FastAPI, pytest)
- Frontend uses TypeScript (React/Vite, vitest)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["4.1", "4.2"] },
    { "id": 4, "tasks": ["4.3", "6.1", "6.2"] }
  ]
}
```
