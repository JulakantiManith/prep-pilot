# Implementation Plan: AI Interview & Presentation Coach

## Overview

This implementation plan follows a phased approach: Phase 1 (MVP) establishes the core platform with authentication, interview sessions, speech/confidence analysis, AI feedback, analytics, and session history. Phase 2 adds resume-based interviews, presentation coach, and advanced analytics. Phase 3 introduces computer vision features with MediaPipe. Each task builds incrementally on previous work, with checkpoints for validation.

## Tasks

- [x] 1. Project scaffolding and shared infrastructure
  - [x] 1.1 Initialize frontend project with Vite, React, TypeScript, Tailwind CSS, and install dependencies (React Router DOM, TanStack Query, React Hook Form, Zod, Recharts, Axios, shadcn/ui)
    - Create `frontend/` directory with Vite React-TS template
    - Configure `tsconfig.json` with `strict: true`
    - Configure Tailwind CSS and shadcn/ui
    - Set up path aliases (`@/` → `src/`)
    - Create `.env.example` with `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_CREATOR_NAME`, `VITE_GITHUB_URL`, `VITE_LINKEDIN_URL`
    - Verify root-level `.gitignore` already exists (created pre-scaffolding) with proper exclusions for node_modules, dist, build, .env files, Python cache, virtual environments, coverage, while preserving .kiro/specs/ and documentation
    - _Requirements: 18.1, 18.5, 18.6_

  - [x] 1.2 Initialize backend project with FastAPI, Python, and install dependencies (pydantic, supabase-py, openai, google-generativeai, python-multipart, hypothesis)
    - Create `backend/` directory with FastAPI project structure following the design's clean architecture
    - Create `app/main.py`, `app/config.py`, `app/dependencies.py`
    - Create directory structure: `api/routes/`, `api/middleware/`, `api/schemas/`, `services/`, `models/`, `repositories/`, `integrations/`, `utils/`
    - Create `requirements.txt` with pinned versions
    - Create `.env.example` with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `WHISPER_API_KEY`, `DATABASE_URL`, `JWT_SECRET`
    - _Requirements: 18.1, 18.3, 18.4, 18.5_

  - [x] 1.3 Set up frontend app shell with providers, routing, and layout components
    - Create `src/app/App.tsx`, `src/app/routes.tsx`, `src/app/providers.tsx` (QueryClientProvider, ThemeProvider, Router)
    - Create `src/shared/components/Layout.tsx`, `Navbar.tsx`, `Sidebar.tsx`, `LoadingSpinner.tsx`, `ErrorMessage.tsx`
    - Create `src/shared/lib/axios.ts` (Axios instance with base URL, interceptors for auth tokens and 401 handling)
    - Create `src/shared/lib/supabase.ts` (Supabase client initialization)
    - Create `src/shared/lib/utils.ts`
    - Create `src/shared/types/index.ts` with shared TypeScript interfaces
    - _Requirements: 15.1, 18.5, 18.6_

  - [x] 1.4 Create Footer component with configurable creator info via environment variables
    - Create `src/shared/components/Footer.tsx` with creator name, GitHub link, LinkedIn link, copyright year
    - Read values from `VITE_CREATOR_NAME`, `VITE_GITHUB_URL`, `VITE_LINKEDIN_URL`
    - All links open in new tab with `rel="noopener noreferrer"`
    - Responsive layout across desktop, tablet, and mobile
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7_

  - [x] 1.5 Create ThemeToggle component and dark mode support
    - Create `src/shared/hooks/useTheme.ts` with system preference detection and localStorage persistence
    - Create `src/shared/components/ThemeToggle.tsx`
    - Configure Tailwind dark mode class strategy
    - Default to OS preferred color scheme for first-time visitors
    - _Requirements: 15.2, 15.3, 15.4_

  - [x] 1.6 Set up backend middleware (error handler, auth middleware, CORS)
    - Create `app/api/middleware/error_handler.py` with global exception handler returning structured `ErrorResponse`
    - Create `app/api/middleware/auth_middleware.py` for JWT verification via Supabase
    - Configure CORS for frontend origin
    - Define `ErrorResponse` and `FieldError` Pydantic models in `app/api/schemas/common_schemas.py`
    - _Requirements: 17.2, 17.5_

  - [x] 1.7 Create database models and Supabase integration client
    - Create `app/integrations/supabase_client.py` with Supabase client initialization
    - Create `app/models/user.py`, `app/models/session.py`, `app/models/answer.py`, `app/models/feedback.py`, `app/models/analytics.py`
    - Define Pydantic models matching database schema (SessionType, InterviewType, Difficulty, SessionStatus enums)
    - _Requirements: 16.1, 16.4_

- [x] 2. Authentication feature (Phase 1)
  - [x] 2.1 Implement backend auth routes and service
    - Create `app/api/routes/auth.py` with POST endpoints: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/forgot-password`, `/api/v1/auth/reset-password`
    - Create `app/services/auth_service.py` wrapping Supabase Auth methods
    - Create `app/api/schemas/auth_schemas.py` with Zod-equivalent Pydantic validation (email format, password strength, required fields)
    - Ensure forgot-password returns identical response regardless of email existence
    - Ensure login failure returns generic error message
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8_

  - [x] 2.2 Implement frontend auth feature (login, register, forgot password, reset password pages and forms)
    - Create `src/features/auth/schemas/authSchemas.ts` with Zod schemas for registration, login, forgot-password, reset-password
    - Create `src/features/auth/services/authService.ts` with API calls and Supabase client auth methods
    - Create `src/features/auth/hooks/useAuth.ts` with authentication state management
    - Create `src/features/auth/components/LoginForm.tsx`, `RegisterForm.tsx`, `ForgotPasswordForm.tsx`, `ResetPasswordForm.tsx`
    - Create `src/features/auth/pages/LoginPage.tsx`, `RegisterPage.tsx`
    - Implement protected route redirect (unauthenticated → login page)
    - Display field-specific validation errors inline
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [ ]* 2.3 Write property tests for auth uniformity (Properties 9, 10, 11)
    - **Property 9: Forgot password response uniformity** — verify identical response for registered and unregistered emails
    - **Property 10: Invalid login error uniformity** — verify generic error for all invalid credential combinations
    - **Property 11: Protected route redirect** — verify 401/redirect for all protected routes when unauthenticated
    - **Validates: Requirements 1.4, 1.6, 1.8**

  - [x] 2.4 Implement auth-aware navbar, logout confirmation, email verification messaging, and PublicOnlyRoute
    - Update `src/shared/components/Navbar.tsx` to use `useAuth()` hook: show user name + logout button when authenticated, show Sign In/Register when unauthenticated
    - Create `src/features/auth/components/LogoutConfirmDialog.tsx` using shadcn/ui AlertDialog pattern: confirmation message, Cancel and Sign Out buttons
    - Update `src/features/auth/components/LoginForm.tsx` to detect unverified email errors from Supabase (`email_not_confirmed`) and display "Please verify your email address before signing in"
    - Create `src/features/auth/components/PublicOnlyRoute.tsx`: redirect authenticated users to /dashboard with `replace: true`
    - Update `src/app/routes.tsx` to wrap /login, /register, /forgot-password, /reset-password with PublicOnlyRoute
    - Ensure both ProtectedRoute and PublicOnlyRoute use `replace: true` in Navigate for back-button protection
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7_

- [x] 3. Profile management feature (Phase 1)
  - [x] 3.1 Implement backend profile routes and service
    - Create `app/api/routes/profile.py` with GET/PUT `/api/v1/profile` and POST/GET `/api/v1/profile/resume`
    - Create `app/services/profile_service.py` with profile CRUD and file upload to Supabase Storage
    - Create `app/api/schemas/profile_schemas.py` (target_role, experience_level, skills validation)
    - Enforce 10 MB file size limit for resume uploads
    - Restrict file access to owning user
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 16.2_

  - [x] 3.2 Implement frontend profile feature (profile page, resume upload)
    - Create `src/features/profile/services/profileService.ts`
    - Create `src/features/profile/hooks/useProfile.ts`
    - Create `src/features/profile/components/ProfileForm.tsx` (target role, experience level, skills)
    - Create `src/features/profile/components/ResumeUpload.tsx` (file validation, upload progress)
    - Create `src/features/profile/pages/ProfilePage.tsx`
    - Preserve previously entered data on validation errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 3.3 Write property tests for profile and file validation (Properties 13, 14)
    - **Property 13: Profile update round-trip persistence** — save and retrieve returns equivalent data
    - **Property 14: File size validation enforcement** — reject >10MB, accept ≤10MB
    - **Validates: Requirements 2.1, 2.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Interview sessions feature (Phase 1)
  - [ ] 5.1 Implement backend question generator with cache layer and fallback mechanism
    - Create `app/services/question_cache_service.py` with cache key `{interview_type}:{role}:{topic}:{difficulty}`, configurable TTL (default 24h), and invalidation methods
    - Create `app/services/question_generator.py` that checks cache first, falls back to Gemini API on miss, stores result in cache
    - Create `app/integrations/gemini_client.py` with retry logic (1 retry, exponential backoff, 45s timeout)
    - Create `app/services/question_bank_service.py` with predefined question sets categorized by interview type, topic, and difficulty
    - If the Gemini API is unavailable, rate limited, times out, or returns an error after retry, fall back to the predefined question bank
    - Continue the interview session without interruption during AI provider failure
    - Log AI provider failures for monitoring
    - Display a non-blocking notification to the user indicating fallback questions are being used
    - Resume-based questions remain AI-generated only (no fallback for personalized questions)
    - Resume-based questions excluded from caching
    - _Requirements: 4.1, 5.1, 10.4, 17.3_

  - [ ] 5.2 Implement backend transcription and session management
    - Create `app/integrations/whisper_client.py` with transcription within 30 seconds, retry on failure
    - Create `app/services/transcription_service.py`
    - Create `app/services/session_service.py` (create session, submit answer, complete session)
    - Create `app/repositories/session_repository.py` with database operations and retry on write failure
    - Create `app/api/routes/interview.py` with POST `/api/v1/sessions/interview`, POST `/api/v1/sessions/interview/{id}/answers`, POST `/api/v1/sessions/interview/{id}/complete`
    - Create `app/api/schemas/interview_schemas.py`
    - _Requirements: 4.2, 4.3, 4.6, 16.1, 16.3_

  - [ ] 5.3 Implement backend speech analysis service
    - Create `app/services/speech_analysis_service.py` with `analyze(transcript, duration_seconds)` method
    - Compute WPM = total_words / (duration / 60), rounded to nearest integer
    - Detect filler words (um, uh, like, actually, basically, you know) with per-word counts
    - Compute communication score (0-100) based on WPM proximity to 120-160 range, filler frequency, pause patterns
    - Flag WPM outside ideal range via `wpm_in_range` boolean
    - Return `SpeechMetrics` with all required fields
    - _Requirements: 4.4, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 5.4 Implement backend confidence analyzer
    - Create `app/services/confidence_analyzer.py` with `analyze(transcript, hesitation_count, pause_frequency, speech_flow_score, response_completeness)` method
    - Compute confidence score (0-100) based on hesitation, pause frequency, speech flow, completeness
    - Ensure deterministic output for identical inputs
    - Return `ConfidenceResult` model
    - _Requirements: 9.1, 9.2_

  - [ ] 5.5 Implement backend AI feedback service
    - Create `app/services/ai_feedback_service.py` with `generate_feedback(session_data, speech_metrics, confidence_score)` method
    - Generate minimum 2 strengths, 2 weaknesses, 3 recommendations per session
    - Include confidence improvement recommendations when score is 1-49
    - Include technical accuracy evaluation for technical interviews
    - Include communication structure evaluation for non-technical interviews
    - Produce feedback within 45 seconds
    - Return `FeedbackReport` model
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 9.3_

  - [ ] 5.6 Implement technical interview mode (topic selection, difficulty, follow-up questions)
    - Create `app/api/routes/sessions.py` (or extend `interview.py`) with POST `/api/v1/sessions/technical`, POST `/api/v1/sessions/technical/{id}/answers`, GET `/api/v1/sessions/technical/{id}/evaluation`, POST `/api/v1/sessions/technical/{id}/follow-up`
    - Create `app/api/schemas/session_schemas.py` for technical interview schemas
    - Support topics: Data Structures, Algorithms, OS, DBMS, CN, OOP, Java, Python, JavaScript, React, Node.js, Cloud Computing
    - Support difficulty levels: Beginner, Intermediate, Advanced
    - Generate follow-up questions on weak areas
    - Display score breakdown: technical accuracy, completeness, communication
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 5.7 Implement frontend interview setup and session flow
    - Create `src/features/interview/schemas/interviewSchemas.ts` (Zod schemas for interview config)
    - Create `src/features/interview/services/interviewService.ts` (API calls for session lifecycle)
    - Create `src/features/interview/hooks/useInterview.ts` (session state management)
    - Create `src/features/interview/hooks/useAudioRecorder.ts` (MediaRecorder API wrapper)
    - Create `src/features/interview/components/InterviewSetup.tsx` (type, role, topic, difficulty selection)
    - Create `src/features/interview/components/QuestionDisplay.tsx`
    - Create `src/features/interview/components/AudioRecorder.tsx` (record/stop, microphone permission handling)
    - Create `src/features/interview/components/AnswerFeedback.tsx` (per-answer analysis display)
    - Create `src/features/interview/components/SessionReport.tsx` (final score report)
    - Create `src/features/interview/pages/InterviewSetupPage.tsx`, `InterviewSessionPage.tsx`
    - Handle microphone access denial with clear error message
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.2, 5.3, 5.4_

  - [ ]* 5.8 Write property tests for speech analysis (Properties 1-5)
    - **Property 1: Speech analysis produces valid metrics** — non-empty transcript + positive duration → valid SpeechMetrics
    - **Property 2: WPM calculation correctness** — WPM = W / (D / 60) rounded
    - **Property 3: Filler word detection accuracy** — correct count and per-word breakdown
    - **Property 4: Communication score bounds and monotonicity** — score in [0,100], better metrics → higher score
    - **Property 5: WPM range flag correctness** — true iff WPM in [120,160]
    - **Validates: Requirements 4.4, 7.3, 8.1, 8.2, 8.3, 8.4, 8.5**

  - [ ]* 5.9 Write property tests for confidence analyzer (Property 6)
    - **Property 6: Confidence score bounds and determinism** — score in [0,100], deterministic, monotonic
    - **Validates: Requirements 9.1, 9.2**

  - [ ]* 5.10 Write property tests for AI feedback (Properties 7, 8)
    - **Property 7: Low confidence triggers improvement recommendations** — confidence 1-49 → confidence recommendation
    - **Property 8: Feedback minimum structure** — at least 2 strengths, 2 weaknesses, 3 recommendations
    - **Validates: Requirements 9.3, 10.2**

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Dashboard feature (Phase 1)
  - [ ] 7.1 Implement backend dashboard/analytics overview endpoint
    - Create `app/api/routes/analytics.py` with GET `/api/v1/analytics/overview`
    - Create `app/services/analytics_service.py` with aggregate metrics computation (total interview sessions, total presentation sessions, average score, latest confidence/communication scores)
    - Create `app/repositories/analytics_repository.py`
    - Return weekly progress chart data for current week
    - Return 5 most recent sessions (type, date, score)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 7.2 Implement frontend dashboard feature
    - Create `src/features/dashboard/services/dashboardService.ts`
    - Create `src/features/dashboard/hooks/useDashboard.ts`
    - Create `src/features/dashboard/components/MetricsCards.tsx` (total sessions, avg score, confidence, communication)
    - Create `src/features/dashboard/components/WeeklyChart.tsx` (Recharts line chart for score trends)
    - Create `src/features/dashboard/components/RecentSessions.tsx` (latest 5 sessions list)
    - Create `src/features/dashboard/components/OnboardingState.tsx` (welcome message + CTA for zero sessions)
    - Create `src/features/dashboard/pages/DashboardPage.tsx`
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

  - [ ]* 7.3 Write property tests for dashboard aggregation (Property 15)
    - **Property 15: Dashboard aggregation correctness** — correct counts, averages, and latest scores
    - **Validates: Requirements 3.1**

- [ ] 8. Analytics and session history features (Phase 1)
  - [ ] 8.1 Implement backend analytics progress and trends endpoints
    - Extend `app/api/routes/analytics.py` with GET `/api/v1/analytics/progress` and GET `/api/v1/analytics/trends`
    - Create `app/api/schemas/analytics_schemas.py` (time range filters, response schemas)
    - Implement daily/weekly/monthly bucketing
    - Compute independent trends for overall_score, confidence_score, communication_score
    - Filter metrics by selected time range
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ] 8.2 Implement frontend analytics feature
    - Create `src/features/analytics/services/analyticsService.ts`
    - Create `src/features/analytics/hooks/useAnalytics.ts`
    - Create `src/features/analytics/components/ScoreTrendChart.tsx` (Recharts line charts)
    - Create `src/features/analytics/components/SessionFrequencyChart.tsx` (Recharts bar chart)
    - Create `src/features/analytics/components/TimeRangeSelector.tsx` (daily/weekly/monthly toggle)
    - Create `src/features/analytics/components/MetricBreakdown.tsx`
    - Create `src/features/analytics/pages/AnalyticsPage.tsx`
    - Show encouraging message when fewer than 3 sessions
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ] 8.3 Implement backend session history endpoints
    - Create `app/api/routes/history.py` with GET `/api/v1/history` (paginated, filtered) and GET `/api/v1/history/{id}` (full detail)
    - Implement pagination (20 per page), sorting by date descending
    - Implement filtering by session_type and date_range
    - Return session_type, date, duration, overall_score for list entries
    - Return full transcript, all scores, AI feedback, and metadata for detail view
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ] 8.4 Implement frontend session history feature
    - Create `src/features/history/services/historyService.ts`
    - Create `src/features/history/hooks/useSessionHistory.ts`
    - Create `src/features/history/components/SessionList.tsx` (paginated list)
    - Create `src/features/history/components/SessionCard.tsx` (type, date, duration, score)
    - Create `src/features/history/components/SessionDetail.tsx` (full transcript, scores, feedback)
    - Create `src/features/history/components/SessionFilters.tsx` (type filter, date range)
    - Create `src/features/history/pages/HistoryPage.tsx`, `SessionDetailPage.tsx`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 8.5 Write property tests for analytics and history (Properties 16-21)
    - **Property 16: Time period bucketing correctness** — sessions correctly bucketed by day/week/month
    - **Property 17: Session list sorted by date with correct limiting** — descending order, min(5,N) for dashboard
    - **Property 18: Session filtering by type and time range** — exact match of filter criteria
    - **Property 19: Analytics trend computation per category** — independent series with correct averages per bucket
    - **Property 20: Pagination correctness** — 20 per page, ceil(N/20) pages, no duplicates, complete union
    - **Property 21: Session list entries include required fields** — non-null session_type, created_at, duration_seconds, overall_score
    - **Validates: Requirements 3.2, 3.3, 11.1, 11.3, 11.4, 12.1, 12.2, 12.4, 12.5**

- [ ] 9. Landing page feature (Phase 1)
  - [ ] 9.1 Implement frontend landing page
    - Create `src/features/landing/components/Hero.tsx` (hero section with CTA)
    - Create `src/features/landing/components/Features.tsx` (features section)
    - Create `src/features/landing/components/HowItWorks.tsx`
    - Create `src/features/landing/components/Benefits.tsx`
    - Create `src/features/landing/components/Testimonials.tsx`
    - Create `src/features/landing/components/Pricing.tsx`
    - Create `src/features/landing/components/FAQ.tsx`
    - Create `src/features/landing/pages/LandingPage.tsx` (assembles all sections)
    - CTA buttons navigate to registration page
    - Include Footer component on landing page
    - Responsive across desktop, tablet, mobile viewports
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 10. Input validation and error handling (Phase 1)
  - [ ] 10.1 Implement shared validation schemas and client/server consistency
    - Ensure all frontend Zod schemas match backend Pydantic schemas for field requirements and formats
    - Implement server-side validation returning 422 with `{detail: [{field, message, type}]}` structure
    - Implement Axios response interceptor for displaying structured errors
    - Implement retry logic for network errors with user-friendly messages
    - _Requirements: 17.2, 17.4, 17.5_

  - [ ]* 10.2 Write property tests for validation (Properties 12, 27)
    - **Property 12: Input validation produces field-specific structured errors** — invalid fields return 422 with named errors
    - **Property 27: Client/server validation consistency** — same input yields same accept/reject on both sides
    - **Validates: Requirements 1.7, 17.4, 17.5**

- [ ] 11. Checkpoint - Ensure all Phase 1 tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Resume-based interviews feature (Phase 2)
  - [ ] 12.1 Implement backend resume parsing with manual editing fallback
    - Create `app/services/resume_parser.py` with extraction of skills, projects, experience, education from PDF/DOCX
    - Create `app/api/routes/resume.py` with POST `/api/v1/resume/parse`, GET `/api/v1/resume/extracted/{id}`, PUT `/api/v1/resume/extracted/{id}`, POST `/api/v1/resume/confirm/{id}`
    - Extract within 60 seconds, include confidence score
    - Support manual editing of all extracted fields (skills, projects, experience, education)
    - Questions generated ONLY after user confirms extracted data
    - Handle extraction failure with error message
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 12.2 Implement frontend resume-based interview flow
    - Create editable form displaying extracted resume data (highlighted low-confidence fields)
    - Create confirmation step before question generation
    - Wire into existing interview session flow for resume-based questions
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 13. Presentation coach feature (Phase 2)
  - [ ] 13.1 Implement backend presentation session endpoints
    - Create `app/services/presentation_service.py` (presentation-specific analysis: speed, clarity, structure, communication, engagement)
    - Create `app/api/routes/presentation.py` with POST `/api/v1/sessions/presentation`, POST `/{id}/recording`, POST `/{id}/materials`, POST `/{id}/complete`
    - Create `app/api/schemas/presentation_schemas.py`
    - Generate presentation-specific scores and improvement suggestions
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 13.2 Implement frontend presentation coach feature
    - Create `src/features/presentation/hooks/useVideoRecorder.ts` (audio + video MediaRecorder)
    - Create `src/features/presentation/services/presentationService.ts`
    - Create `src/features/presentation/hooks/usePresentation.ts`
    - Create `src/features/presentation/components/PresentationSetup.tsx`
    - Create `src/features/presentation/components/PresentationRecorder.tsx` (audio + video recording)
    - Create `src/features/presentation/components/PresentationReport.tsx` (category score breakdown)
    - Create `src/features/presentation/pages/PresentationSetupPage.tsx`, `PresentationSessionPage.tsx`
    - Support PPT/PDF material upload
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 14. Checkpoint - Ensure all Phase 2 tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Eye contact and head pose analysis (Phase 3)
  - [ ] 15.1 Implement backend MediaPipe integration for eye contact and head pose
    - Create `app/integrations/mediapipe_client.py` with face mesh and gaze detection
    - Implement eye contact percentage calculation (camera frames / total frames × 100)
    - Implement head pose estimation (pitch, yaw, roll) with stability classification
    - Handle face not detected / low lighting with warning response
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [ ] 15.2 Implement frontend visual analysis display
    - Add real-time eye gaze overlay during video sessions
    - Display eye contact percentage and head movement stability metrics in session reports
    - Display lighting/positioning warnings during recording
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [ ]* 15.3 Write property tests for visual analysis (Properties 22, 23)
    - **Property 22: Eye contact percentage calculation** — (camera_frames / total_frames) × 100, rounded to 1 decimal
    - **Property 23: Head pose stability classification** — stable when std dev < threshold, excessive otherwise
    - **Validates: Requirements 13.2, 13.4**

- [ ] 16. Data persistence, theme, and security hardening
  - [ ] 16.1 Implement data isolation and persistence guarantees
    - Ensure all repository queries filter by authenticated `user_id`
    - Implement database write retry logic (retry once on failure, display error if retry fails)
    - Ensure session data (transcript, scores, feedback, duration, date) persisted on completion
    - Verify Supabase Storage access restricted to owning user via RLS policies
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [ ] 16.3 Implement theme flash prevention (FOUC)
    - Add an inline blocking `<script>` in `frontend/index.html` (inside `<head>`, before any module scripts) that reads the saved theme from `localStorage` key `theme-preference`, resolves `"system"` via `window.matchMedia("(prefers-color-scheme: dark)")`, and applies the `"dark"` or `"light"` class to `document.documentElement` synchronously
    - The inline script must use the same `localStorage` key (`theme-preference`) and resolution logic as `ThemeContext.tsx` to ensure consistency
    - If `localStorage` is unavailable or the stored value is invalid, fall back to the OS preferred color scheme
    - Verify that on page load/refresh with dark mode saved, no white flash is visible before React hydrates
    - Verify that client-side route navigation preserves the active theme class without visual flicker
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5_

  - [ ]* 16.2 Write property tests for persistence and isolation (Properties 24, 25, 26)
    - **Property 24: Theme preference persistence round-trip** — save "light"/"dark", retrieve same value
    - **Property 25: Session data persistence round-trip** — persist and retrieve returns equivalent data
    - **Property 26: Data isolation per user** — user A never sees user B's data
    - **Validates: Requirements 15.3, 16.1, 16.4**

- [ ] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Tasks marked with `*` (property tests) are lower priority than core feature implementation — core functionality should be completed before optional property tests are implemented
- Property tests within the same phase should come after their corresponding feature tasks
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at phase boundaries
- Property tests validate universal correctness properties defined in the design
- Unit tests validate specific examples and edge cases
- All API endpoints use `/api/v1/` prefix
- The question cache layer reduces Gemini API costs by avoiding duplicate calls
- Resume-based questions are never cached (personalized per user)
- Footer creator info is always read from environment variables, never hardcoded

### MVP Priority Enforcement

- Before implementing Phase 2 or Phase 3 features, ALL Phase 1 tasks must be completed and passing
- Phase 1 must build successfully with functional auth, interview sessions, analytics, and dashboard
- Tasks are already in dependency order; this is an explicit enforcement note

### Architecture Rules

- No source file may exceed 600 lines — split large files into reusable modules
- Follow feature-based architecture (co-located components, hooks, services, schemas)
- Follow SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)
- Use strict TypeScript mode (`strict: true` in tsconfig)
- Keep business logic outside UI components — use dedicated service or utility modules
- Keep API communication in dedicated service files (e.g., `authService.ts`, `interviewService.ts`)
- Shared UI components live in `shared/components/` accessible to all feature modules

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "1.5", "1.6", "1.7"] },
    { "id": 2, "tasks": ["2.1", "2.2"] },
    { "id": 3, "tasks": ["2.3", "2.4", "3.1", "3.2"] },
    { "id": 4, "tasks": ["3.3", "5.1", "5.2"] },
    { "id": 5, "tasks": ["5.3", "5.4", "5.5"] },
    { "id": 6, "tasks": ["5.6", "5.7"] },
    { "id": 7, "tasks": ["5.8", "5.9", "5.10", "7.1"] },
    { "id": 8, "tasks": ["7.2", "7.3", "8.1", "8.3"] },
    { "id": 9, "tasks": ["8.2", "8.4", "8.5"] },
    { "id": 10, "tasks": ["9.1", "10.1"] },
    { "id": 11, "tasks": ["10.2"] },
    { "id": 12, "tasks": ["12.1", "13.1"] },
    { "id": 13, "tasks": ["12.2", "13.2"] },
    { "id": 14, "tasks": ["15.1"] },
    { "id": 15, "tasks": ["15.2", "15.3"] },
    { "id": 16, "tasks": ["16.1", "16.3"] },
    { "id": 17, "tasks": ["16.2"] }
  ]
}
```
