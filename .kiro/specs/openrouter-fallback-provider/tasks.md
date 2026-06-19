# Implementation Plan: OpenRouter Fallback Provider

## Overview

Minimal implementation adding OpenRouter (openrouter/free) as a fallback AI provider when Gemini is rate-limited or unavailable. No health monitoring, capability registry, circuit breakers, or advanced logging. Just: try Gemini → on failure, try OpenRouter → on failure, use existing service-level fallbacks (question bank, algorithmic feedback).

## Tasks

- [x] 1. OpenRouter client and configuration
  - [x] 1.1 Add OpenRouter API key to configuration
    - Add `openrouter_api_key` field to `Settings` in `backend/app/config.py`
    - Add `OPENROUTER_API_KEY` to `backend/.env.example`
    - _Requirements: 9.1, 9.4_

  - [x] 1.2 Create OpenRouter client
    - Create `backend/app/integrations/openrouter_client.py`
    - Implement `OpenRouterClient` class with `generate(prompt)` async method
    - Call `https://openrouter.ai/api/v1/chat/completions` with model `openrouter/free`
    - Authenticate with `Authorization: Bearer {OPENROUTER_API_KEY}`
    - Enforce 45-second timeout
    - Extract text from `choices[0].message.content`
    - Handle HTTP errors (429, 500, 503) with descriptive `OpenRouterClientError`
    - Expose `is_configured` property that returns False when API key is missing
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Add fallback to Gemini client
  - [x] 2.1 Add OpenRouter fallback to `_call_gemini` method
    - **ALREADY DONE**: `GeminiClient._call_with_fallback()` already implements: Gemini retry (1 attempt with backoff) → OpenRouter fallback → raise GeminiClientError if both fail. Skips fallback when API key is missing. Logs provider switch.
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 8.2, 8.3_

- [x] 3. Update resume parser to use fallback
  - [x] 3.1 Wire OpenRouter fallback into resume parser
    - **ALREADY DONE**: `ResumeParser` calls `GeminiClient._call_with_fallback(prompt)` directly, which automatically falls back to OpenRouter after Gemini retries are exhausted. No duplicate fallback logic needed.
    - _Requirements: 3.5, 7.3_

- [x] 4. Verify all services work with fallback
  - [x] 4.1 Verify question generation uses fallback
    - **VERIFIED**: `QuestionGenerator` calls `GeminiClient.generate_questions()` which uses `_call_with_fallback()` internally. On `GeminiClientError`, it falls back to the predefined question bank via `_fallback_to_question_bank()`.
    - _Requirements: 7.1, 7.4_

  - [x] 4.2 Verify AI feedback generation uses fallback
    - **VERIFIED**: `AIFeedbackService._call_gemini()` calls `self._gemini._call_with_fallback(prompt)` directly. If both providers fail, it falls back to `_generate_algorithmic_feedback()`.
    - _Requirements: 7.2, 7.5_

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1.1", "1.2"] },
    { "wave": 2, "tasks": ["2.1"] },
    { "wave": 3, "tasks": ["4.1", "4.2"] }
  ]
}
```

## Notes

- This is a minimal implementation. The Gemini client already has retry logic (1 retry with backoff). The fallback to OpenRouter happens AFTER that retry is exhausted.
- No new abstractions or interfaces are introduced. OpenRouter is wired directly as a secondary call in the existing `_call_gemini` path.
- If `OPENROUTER_API_KEY` is not set, the system behaves exactly as before (Gemini only).
- Existing service-level fallbacks (question bank, algorithmic feedback) remain as the final safety net when both providers fail.
