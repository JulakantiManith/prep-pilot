# Implementation Plan: Interview Background Evaluation

## Overview

Convert the interview session completion flow from synchronous blocking to asynchronous non-blocking processing. The backend will return HTTP 202 immediately, process results via `asyncio.create_task`, and the frontend will display a success screen with navigation options. This mirrors the existing presentation module pattern.

## Tasks

- [ ] 1. Backend: Add `PROCESSING` status and response schemas
  - [ ] 1.1 Add `PROCESSING` status to `SessionStatus` enum and create new response schemas
    - Add `PROCESSING = "processing"` to the `SessionStatus` enum in `app/models/session.py`
    - Create `AcceptedSessionResponse` schema in `app/api/schemas/interview_schemas.py` with `session_id: str` and `status: str`
    - Create `SessionStatusResponse` schema with `session_id`, `status`, optional `scores` (reuse `ScoreSummary`), optional `feedback` (reuse `FeedbackResponse`), and optional `technical_evaluation` field
    - Create `TechnicalEvaluationData` schema with `evaluations` list and `average_scores` dict for the status response
    - _Requirements: 1.2, 1.3, 3.3, 5.2, 5.3_

- [ ] 2. Backend: Convert completion endpoint to async 202 pattern
  - [ ] 2.1 Modify `complete_session` endpoint to return HTTP 202 and launch background task
    - Change the `POST /sessions/interview/{session_id}/complete` endpoint in `app/api/routes/interview.py`
    - Verify session exists and belongs to user (return 404 if not)
    - Check session status is `in_progress` (return 400 if `completed` or `processing`)
    - Update session status to `processing` in the database
    - Launch background processor via `asyncio.create_task`
    - Return `AcceptedSessionResponse` with HTTP 202 status code
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ] 2.2 Implement `_run_interview_evaluation_background` function
    - Create the background processor function in `app/api/routes/interview.py`
    - Wrap entire pipeline in `asyncio.wait_for` with 120-second timeout
    - Implement the processing pipeline: retrieve answers → relevance scoring (non-critical) → aggregate score computation (critical) → persist scores (critical) → AI feedback generation (non-critical) → persist feedback (non-critical) → email notification (non-critical) → update status to `completed`
    - On `asyncio.TimeoutError`: mark session as `failed`
    - On critical step exception: mark session as `failed`
    - On non-critical step exception: log warning, skip step, continue
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.3 Write property tests for completion endpoint (Properties 1-3)
    - **Property 1: Completion endpoint returns 202 and transitions to processing**
    - **Property 2: Completion rejects already-processing or completed sessions**
    - **Property 3: Completion returns 404 for non-existent or unauthorized sessions**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 6.4**

  - [ ]* 2.4 Write property tests for background processor (Properties 4-6)
    - **Property 4: Successful background processing persists scores and completes**
    - **Property 5: Critical step failure marks session as failed**
    - **Property 6: Non-critical step failure still completes session**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5**

- [ ] 3. Backend: Implement status polling endpoint
  - [ ] 3.1 Add `GET /sessions/interview/{session_id}/status` endpoint
    - Add the status endpoint to `app/api/routes/interview.py`
    - Require authentication via `CurrentUserDep`
    - Validate UUID format (FastAPI handles via path param type annotation)
    - Verify session exists and belongs to requesting user (return 404 if not)
    - Return current status for `in_progress`, `processing`, `failed` states
    - For `completed` standard sessions: return scores and feedback data
    - For `completed` technical sessions: return per-answer evaluations and aggregate averages
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 3.2 Write property tests for status endpoint (Properties 8-12)
    - **Property 8: Status endpoint reflects current session status**
    - **Property 9: Status endpoint returns full data for completed standard sessions**
    - **Property 10: Status endpoint returns full data for completed technical sessions**
    - **Property 11: Invalid UUID returns 422 from status endpoint**
    - **Property 12: Status endpoint returns 404 for unauthorized sessions**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 5.3**

- [ ] 4. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Backend: Technical session async completion
  - [ ] 5.1 Add `POST /sessions/technical/{session_id}/complete` endpoint with 202 pattern
    - Add a new completion endpoint to `app/api/routes/sessions.py`
    - Same validation pattern as standard interview: check ownership (404), check status (400 for completed/processing)
    - Update status to `processing`, launch background task, return `AcceptedSessionResponse` with HTTP 202
    - _Requirements: 5.1_

  - [ ] 5.2 Implement `_run_technical_evaluation_background` function
    - Create the technical background processor function in `app/api/routes/sessions.py`
    - Wrap in `asyncio.wait_for` with 120-second timeout
    - Processing pipeline: retrieve answers → evaluate each answer technically (non-critical per-answer, skip individual failures) → compute aggregate averages (critical) → persist per-answer evaluations and aggregates (critical) → AI feedback (non-critical) → update status to `completed`
    - On timeout or critical failure: mark session as `failed`
    - On individual answer evaluation failure: skip that answer, continue remaining
    - _Requirements: 5.1, 5.2, 5.5_

  - [ ]* 5.3 Write property test for technical partial failure (Property 7)
    - **Property 7: Technical evaluation partial failure still completes**
    - **Validates: Requirements 5.5**

- [ ] 6. Frontend: Update interview service with new API functions
  - [ ] 6.1 Add `completeInterviewSessionAsync` and `getInterviewStatus` functions to `interviewService.ts`
    - Add `AcceptedSessionResponse` interface with `session_id` and `status` fields
    - Add `SessionStatusResponse` interface matching the backend response schema
    - Modify `completeInterviewSession` to expect a 202 response and return `AcceptedSessionResponse`
    - Add `getInterviewStatus(sessionId: string): Promise<SessionStatusResponse>` function calling `GET /sessions/interview/{session_id}/status`
    - Add `completeTechnicalSession(sessionId: string): Promise<AcceptedSessionResponse>` function calling `POST /sessions/technical/{session_id}/complete`
    - _Requirements: 1.3, 3.3, 5.1_

- [ ] 7. Frontend: Create InterviewSuccessScreen component
  - [ ] 7.1 Create `InterviewSuccessScreen.tsx` component
    - Create new file at `frontend/src/features/interview/components/InterviewSuccessScreen.tsx`
    - Display a success icon (checkmark in green circle using lucide-react)
    - Display heading: "Session Submitted!"
    - Display body text: "Your results are being generated. Check the History page for full results."
    - Render exactly 3 navigation buttons: "New Session" (navigates to interview setup), "View History" (navigates to history page), "Dashboard" (navigates to dashboard)
    - Use existing UI components (Button from shared/ui) and Tailwind styling consistent with the project
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 7.2 Write unit tests for InterviewSuccessScreen component
    - Test that success icon, heading, and body text render correctly
    - Test that exactly 3 navigation buttons are present with correct labels
    - Test that buttons navigate to correct routes
    - _Requirements: 4.2, 4.3, 4.4_

- [ ] 8. Frontend: Modify useInterview hook for async completion flow
  - [ ] 8.1 Update `useInterview` hook to handle 202 response and transition to submitted phase
    - Add `"submitted"` to the `InterviewPhase` type
    - Modify `completeSession` to: call the completion API, on 202 response transition phase to `"submitted"`, call `clearStorage()` to clear persisted session state
    - Add error handling: on network/server error, set error state with message but preserve session state (don't clear storage)
    - Add a `retryComplete` function that re-sends the completion request
    - For technical sessions: call `completeTechnicalSession` instead of `getTechnicalEvaluation`
    - Remove the synchronous wait for report/evaluation data from the completion flow
    - _Requirements: 4.1, 4.5, 4.6, 6.1, 6.2_

  - [ ]* 8.2 Write property test for session storage clearing (Property 13)
    - **Property 13: Session storage is cleared on submission**
    - **Validates: Requirements 4.6**

- [ ] 9. Frontend: Update InterviewSessionPage to render success screen
  - [ ] 9.1 Modify `InterviewSessionPage.tsx` to show success screen and handle errors
    - Import and render `InterviewSuccessScreen` when `phase === "submitted"`
    - Add error state UI with error message banner and retry button for failed submissions
    - Remove loading spinner / blocking overlay for the completion phase
    - Remove or disable `beforeunload` event listener when phase is `"submitted"`
    - Ensure navigation is not blocked when on the success screen (no confirmation dialogs)
    - _Requirements: 4.1, 4.5, 6.1, 6.2_

  - [ ]* 9.2 Write unit tests for InterviewSessionPage submission flow
    - Test that success screen is rendered when phase is "submitted"
    - Test that error state shows error message and retry button
    - Test that retry button re-sends completion request
    - Test that no confirmation dialog blocks navigation from success screen
    - _Requirements: 4.1, 4.5, 6.1, 6.2_

- [ ] 10. Frontend: Display failed status on History page
  - [ ] 10.1 Add visual status label for failed sessions on the History page
    - In the history page session list, check for `status === "failed"` and display a visible badge/label indicating background processing failed
    - _Requirements: 6.3_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Integration wiring and final verification
  - [ ] 12.1 Wire all components together and verify end-to-end flow
    - Ensure the interview route imports and registers the new status endpoint
    - Ensure the technical session route imports and registers the new complete endpoint
    - Verify the frontend service functions point to the correct API paths
    - Verify the useInterview hook correctly calls the updated service functions
    - Verify InterviewSessionPage correctly transitions through all phases: in_progress → submitted → success screen
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

  - [ ]* 12.2 Write integration tests for end-to-end completion flow
    - Test: submit completion → receive 202 → poll status → verify completed (with mocked AI services)
    - Test: timeout scenario with slow mock → verify session marked failed after 120s
    - Test: concurrent completion attempts → one 202, one 400
    - _Requirements: 1.1, 2.2, 2.6, 6.4_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The existing presentation module (`app/api/routes/presentation.py`) serves as the reference implementation for the `asyncio.create_task` + status polling pattern
- Backend uses Python (FastAPI, Pydantic, asyncio), frontend uses TypeScript (React, Vite, Vitest)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "6.1"] },
    { "id": 2, "tasks": ["2.2", "5.1", "7.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "5.2", "7.2", "8.1"] },
    { "id": 4, "tasks": ["3.2", "5.3", "8.2", "9.1"] },
    { "id": 5, "tasks": ["9.2", "10.1"] },
    { "id": 6, "tasks": ["12.1"] },
    { "id": 7, "tasks": ["12.2"] }
  ]
}
```
