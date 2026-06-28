# Requirements Document

## Introduction

This feature converts the interview session completion flow from a synchronous blocking pattern to an asynchronous non-blocking pattern. Currently, after completing all interview questions, the user is blocked on a loading spinner while AI scoring, relevance analysis, and feedback generation execute. The desired behavior mirrors the presentation module: the backend returns immediately with HTTP 202, processes results in the background, and the frontend shows a success screen that lets users navigate away without waiting.

## Glossary

- **Interview_Backend**: The FastAPI backend service handling interview session endpoints (`/sessions/interview/`)
- **Interview_Frontend**: The React frontend components for the interview session flow (InterviewSessionPage, useInterview hook, interviewService)
- **Background_Processor**: The asyncio background task that performs relevance scoring, aggregate computation, AI feedback generation, and email notification after session submission
- **Status_Endpoint**: The GET endpoint that allows clients to poll for session processing progress and results
- **Session_Status**: The current state of a session, one of: `in_progress`, `processing`, `completed`, `failed`
- **Success_Screen**: The non-blocking UI displayed immediately after session submission, showing confirmation and navigation options
- **History_Page**: The existing page where users can view completed session results

## Requirements

### Requirement 1: Immediate Session Submission Response

**User Story:** As an interview user, I want the session completion to return immediately after I finish all questions, so that I am not blocked waiting for AI processing.

#### Acceptance Criteria

1. WHEN the user submits a completion request for an interview session that has Session_Status `in_progress`, THE Interview_Backend SHALL return HTTP 202 Accepted within 2 seconds of receiving the request
2. WHEN the Interview_Backend receives a valid completion request, THE Interview_Backend SHALL update the session Session_Status to `processing` before returning the 202 response
3. WHEN the Interview_Backend returns the 202 response, THE Interview_Backend SHALL include a JSON response body containing the session_id and a Session_Status field with value `processing`
4. IF the session has Session_Status `completed` or `processing`, THEN THE Interview_Backend SHALL return HTTP 400 with an error message indicating the session cannot be completed again
5. IF the session_id does not exist or the session does not belong to the authenticated user, THEN THE Interview_Backend SHALL return HTTP 404 with an error message indicating the session was not found

### Requirement 2: Background Result Processing

**User Story:** As a system operator, I want interview scoring and feedback to execute as a background task, so that user-facing latency is minimized.

#### Acceptance Criteria

1. WHEN the Interview_Backend marks a session as `processing`, THE Background_Processor SHALL execute relevance scoring, aggregate score computation, AI feedback generation, and email notification without blocking the HTTP response that triggered the processing
2. WHEN the Background_Processor completes all processing steps successfully, THE Background_Processor SHALL update the Session_Status to `completed`
3. WHEN the Background_Processor completes successfully, THE Background_Processor SHALL persist the overall_score, confidence_score, communication_score, and AI-generated feedback (strengths, weaknesses, recommendations) to the database
4. IF the Background_Processor encounters a failure in the database persistence step or the aggregate score computation step, THEN THE Background_Processor SHALL update the Session_Status to `failed`
5. IF the Background_Processor encounters a failure in the relevance scoring, AI feedback generation, or email notification step, THEN THE Background_Processor SHALL skip the failed step, continue processing remaining steps, and mark the session as `completed`
6. IF the Background_Processor does not complete all processing steps within 120 seconds of the session being marked as `processing`, THEN THE Background_Processor SHALL update the Session_Status to `failed`

### Requirement 3: Session Status Polling Endpoint

**User Story:** As a frontend client, I want to poll the processing status of an interview session, so that I can retrieve results when they are ready.

#### Acceptance Criteria

1. THE Status_Endpoint SHALL be accessible at `GET /sessions/interview/{session_id}/status` and SHALL require a valid authentication token identifying the requesting user
2. WHEN polled for a session with Session_Status `in_progress`, THE Status_Endpoint SHALL return HTTP 200 with a JSON response containing the status value `in_progress`
3. WHEN polled for a session with Session_Status `completed`, THE Status_Endpoint SHALL return HTTP 200 with a JSON response containing the status value `completed`, the session scores (overall_score, confidence_score, communication_score each as integers from 0 to 100), and the feedback data (strengths, weaknesses, and recommendations as arrays of strings)
4. WHEN polled for a session with Session_Status `failed`, THE Status_Endpoint SHALL return HTTP 200 with a JSON response containing the status value `failed`
5. IF the session_id is not a valid UUID format, THEN THE Status_Endpoint SHALL return HTTP 422 with an error message indicating invalid session identifier format
6. IF the session is not found or does not belong to the requesting user, THEN THE Status_Endpoint SHALL return HTTP 404 with an error message indicating the session was not found
7. THE Status_Endpoint SHALL return a response within 2 seconds under normal operating conditions

### Requirement 4: Non-Blocking Success Screen

**User Story:** As an interview user, I want to see a success confirmation immediately after submitting my session, so that I know my answers were received and can continue using the application.

#### Acceptance Criteria

1. WHEN the Interview_Frontend receives a 202 response from session completion, THE Interview_Frontend SHALL display the Success_Screen within 1 second of receiving the response, replacing the interview session UI entirely
2. THE Success_Screen SHALL display a success icon, a confirmation heading, and an informational message indicating results are being generated
3. THE Success_Screen SHALL display a message directing the user to check the History_Page for full results
4. THE Success_Screen SHALL provide exactly 3 navigation buttons: one to start a new session, one to view the History_Page, and one to return to the dashboard
5. WHILE the Success_Screen is displayed, THE Interview_Frontend SHALL allow the user to navigate away using the provided buttons, sidebar, or browser navigation without displaying confirmation dialogs, loading overlays, or disabling any navigation controls
6. WHEN the Success_Screen is displayed, THE Interview_Frontend SHALL clear the persisted interview session state so that returning to the interview route does not resume the completed session

### Requirement 5: Technical Session Background Evaluation

**User Story:** As a technical interview user, I want the same non-blocking completion experience for technical sessions, so that the behavior is consistent across session types.

#### Acceptance Criteria

1. WHEN a technical session is completed, THE Interview_Backend SHALL return HTTP 202 Accepted within 2 seconds, mark the Session_Status as `processing`, and launch a Background_Processor task that executes technical answer evaluation, aggregate score computation, and AI feedback generation
2. WHEN a technical session Background_Processor completes successfully, THE Background_Processor SHALL persist the per-answer technical evaluation scores (technical_accuracy, completeness, communication each as integers 0-100), per-answer feedback text, per-answer weak_areas list, and aggregate average scores to the database, and update the Session_Status to `completed`
3. WHEN the Status_Endpoint is polled for a technical session with Session_Status `completed`, THE Status_Endpoint SHALL return the status value `completed` along with the per-answer evaluation scores, feedback, weak_areas, and aggregate average scores
4. WHEN the Interview_Frontend receives a 202 response from technical session completion, THE Interview_Frontend SHALL display the same Success_Screen as standard interview sessions, including the success icon, confirmation heading, informational message, and navigation buttons
5. IF the Background_Processor encounters a non-fatal error during a single technical evaluation step, THEN THE Background_Processor SHALL continue processing the remaining answers and steps, and still mark the Session_Status as `completed` with partial results persisted

### Requirement 6: Error Handling and Recovery

**User Story:** As an interview user, I want clear feedback if something goes wrong during submission, so that I know whether to retry or check later.

#### Acceptance Criteria

1. IF the completion request fails with a network or server error before the 202 response, THEN THE Interview_Frontend SHALL display an error message indicating that submission failed and present a retry button, while preserving the session state so that no answers are lost
2. IF the user clicks the retry button after a failed submission, THEN THE Interview_Frontend SHALL re-send the completion request and, upon receiving a 202 response, display the Success_Screen
3. IF the user navigates to the History_Page and the session Session_Status is `failed`, THEN THE History_Page SHALL display a visible status label indicating that background processing failed for that session
4. IF the user re-submits a session that is already in `processing` status, THEN THE Interview_Backend SHALL return HTTP 400 indicating the session is already being processed
