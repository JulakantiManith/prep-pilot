-- ============================================================================
-- AI Interview & Presentation Coach — Supabase Database Migration
-- ============================================================================
-- This migration creates all tables, enables RLS, sets up policies, and adds
-- indexes for the AI Interview Coach application.
--
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ============================================================================

-- ============================================================================
-- DATABASE ER DIAGRAM SUMMARY
-- ============================================================================
--
-- auth.users (Supabase-managed)
--   ├── 1:1  → profiles (user profile settings)
--   ├── 1:N  → sessions (interview/presentation sessions)
--   └── 1:N  → resumes (uploaded resume files)
--
-- sessions
--   ├── 1:N  → answers (individual question answers)
--   └── 1:1  → session_feedback (AI-generated feedback report)
--
-- Relationships:
--   profiles.user_id        → auth.users(id)
--   sessions.user_id        → auth.users(id)
--   answers.session_id      → sessions(id)
--   session_feedback.session_id → sessions(id)
--   resumes.user_id         → auth.users(id)
--
-- ============================================================================

-- ============================================================================
-- 1. EXTENSIONS
-- ============================================================================

-- Enable UUID generation (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 2. CUSTOM TYPES (ENUMS)
-- ============================================================================

DO $$ BEGIN
  CREATE TYPE session_type AS ENUM ('interview', 'presentation');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE interview_type AS ENUM ('hr', 'technical', 'behavioral', 'custom', 'resume_based');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE difficulty_level AS ENUM ('beginner', 'intermediate', 'advanced');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE session_status AS ENUM ('in_progress', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Add 'processing' status for async presentation evaluation
ALTER TYPE session_status ADD VALUE IF NOT EXISTS 'processing';

-- ============================================================================
-- 3. TABLES
-- ============================================================================

-- --------------------------------------------------------------------------
-- PROFILES — User profile and preferences
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  target_role TEXT,
  experience_level TEXT,
  skills TEXT[] DEFAULT '{}',
  theme_preference TEXT DEFAULT 'system',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT profiles_user_id_unique UNIQUE (user_id)
);

-- --------------------------------------------------------------------------
-- SESSIONS — Interview and presentation practice sessions
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  session_type session_type NOT NULL,
  interview_type interview_type,
  role TEXT,
  topic TEXT,
  difficulty difficulty_level,
  overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
  confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
  communication_score INTEGER CHECK (communication_score >= 0 AND communication_score <= 100),
  duration_seconds INTEGER,
  status session_status NOT NULL DEFAULT 'in_progress',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------------
-- ANSWERS — Individual question answers within a session
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS answers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  question_index INTEGER NOT NULL CHECK (question_index >= 0),
  question_text TEXT NOT NULL,
  transcript TEXT,
  wpm INTEGER CHECK (wpm >= 0),
  total_words INTEGER CHECK (total_words >= 0),
  filler_word_count INTEGER CHECK (filler_word_count >= 0),
  filler_words_detail JSONB,
  speaking_duration FLOAT,
  avg_pause_duration FLOAT,
  communication_score INTEGER CHECK (communication_score >= 0 AND communication_score <= 100),
  confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
  ai_evaluation JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT answers_session_question_unique UNIQUE (session_id, question_index)
);

-- --------------------------------------------------------------------------
-- SESSION_FEEDBACK — AI-generated feedback reports
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  strengths TEXT[] NOT NULL DEFAULT '{}',
  weaknesses TEXT[] NOT NULL DEFAULT '{}',
  recommendations TEXT[] NOT NULL DEFAULT '{}',
  technical_evaluation JSONB,
  presentation_scores JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT session_feedback_session_id_unique UNIQUE (session_id)
);

-- --------------------------------------------------------------------------
-- RESUMES — Uploaded resume files and extracted data
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resumes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_size INTEGER NOT NULL CHECK (file_size >= 0),
  extracted_data JSONB,
  extraction_confidence FLOAT CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
  user_confirmed BOOLEAN NOT NULL DEFAULT false,
  extraction_status TEXT,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 4. AUTO-UPDATE TIMESTAMPS (trigger function)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
DO $$ BEGIN
  CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TRIGGER set_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TRIGGER set_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- 5. AUTO-CREATE PROFILE ON USER SIGNUP
-- ============================================================================

-- Drop existing trigger and function to recreate with proper config
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS handle_new_user();

-- Recreate with explicit schema references and proper search_path
-- (Fixes "Database error saving new user" during registration)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  INSERT INTO public.profiles (id, user_id, created_at, updated_at)
  VALUES (
    gen_random_uuid(),
    NEW.id,
    now(),
    now()
  )
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Trigger on auth.users insert
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- 6. ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all user-owned tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;

-- --------------------------------------------------------------------------
-- PROFILES policies
-- --------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- --------------------------------------------------------------------------
-- SESSIONS policies
-- --------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own sessions" ON sessions;
CREATE POLICY "Users can view own sessions"
  ON sessions FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create own sessions" ON sessions;
CREATE POLICY "Users can create own sessions"
  ON sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own sessions" ON sessions;
CREATE POLICY "Users can update own sessions"
  ON sessions FOR UPDATE
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own sessions" ON sessions;
CREATE POLICY "Users can delete own sessions"
  ON sessions FOR DELETE
  USING (auth.uid() = user_id);

-- --------------------------------------------------------------------------
-- ANSWERS policies (access through session ownership)
-- --------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own answers" ON answers;
CREATE POLICY "Users can view own answers"
  ON answers FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sessions
      WHERE sessions.id = answers.session_id
      AND sessions.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can create answers for own sessions" ON answers;
CREATE POLICY "Users can create answers for own sessions"
  ON answers FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM sessions
      WHERE sessions.id = answers.session_id
      AND sessions.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can update own answers" ON answers;
CREATE POLICY "Users can update own answers"
  ON answers FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM sessions
      WHERE sessions.id = answers.session_id
      AND sessions.user_id = auth.uid()
    )
  );

-- --------------------------------------------------------------------------
-- SESSION_FEEDBACK policies (access through session ownership)
-- --------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own feedback" ON session_feedback;
CREATE POLICY "Users can view own feedback"
  ON session_feedback FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sessions
      WHERE sessions.id = session_feedback.session_id
      AND sessions.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can create feedback for own sessions" ON session_feedback;
CREATE POLICY "Users can create feedback for own sessions"
  ON session_feedback FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM sessions
      WHERE sessions.id = session_feedback.session_id
      AND sessions.user_id = auth.uid()
    )
  );

-- --------------------------------------------------------------------------
-- RESUMES policies
-- --------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own resumes" ON resumes;
CREATE POLICY "Users can view own resumes"
  ON resumes FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can upload own resumes" ON resumes;
CREATE POLICY "Users can upload own resumes"
  ON resumes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own resumes" ON resumes;
CREATE POLICY "Users can update own resumes"
  ON resumes FOR UPDATE
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own resumes" ON resumes;
CREATE POLICY "Users can delete own resumes"
  ON resumes FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================================================
-- 7. SERVICE ROLE BYPASS (for backend server-side operations)
-- ============================================================================
-- The Supabase service_role key bypasses RLS by default, so the FastAPI backend
-- can perform all operations without RLS restrictions. No additional policies
-- are needed for server-side access.

-- ============================================================================
-- 8. INDEXES
-- ============================================================================

-- Profiles
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);

-- Sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id_created_at ON sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id_session_type ON sessions(user_id, session_type);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id_status ON sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_completed_at ON sessions(completed_at DESC NULLS LAST);

-- Answers
CREATE INDEX IF NOT EXISTS idx_answers_session_id ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_session_id_question_index ON answers(session_id, question_index);

-- Session Feedback
CREATE INDEX IF NOT EXISTS idx_session_feedback_session_id ON session_feedback(session_id);

-- Resumes
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_user_id_uploaded_at ON resumes(user_id, uploaded_at DESC);

-- ============================================================================
-- 9. STORAGE BUCKETS
-- ============================================================================

-- Resumes bucket (10 MB limit, PDF and DOCX only)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'resumes',
  'resumes',
  false,
  10485760,  -- 10 MB limit
  ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
)
ON CONFLICT (id) DO UPDATE SET
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Recordings bucket (25 MB limit for presentation recordings — supports ~20 min video/audio)
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES (
  'recordings',
  'recordings',
  false,
  26214400  -- 25 MB limit
)
ON CONFLICT (id) DO UPDATE SET
  file_size_limit = EXCLUDED.file_size_limit;

-- Materials bucket (50 MB limit for PPT/PDF presentation slides)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'materials',
  'materials',
  false,
  52428800,  -- 50 MB limit
  ARRAY[
    'application/pdf',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Storage RLS policies for resumes bucket
DROP POLICY IF EXISTS "Users can upload own resumes to storage" ON storage.objects;
CREATE POLICY "Users can upload own resumes to storage"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'resumes'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

DROP POLICY IF EXISTS "Users can view own resumes in storage" ON storage.objects;
CREATE POLICY "Users can view own resumes in storage"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'resumes'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

DROP POLICY IF EXISTS "Users can delete own resumes from storage" ON storage.objects;
CREATE POLICY "Users can delete own resumes from storage"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'resumes'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

-- Storage RLS policies for recordings bucket
DROP POLICY IF EXISTS "Users can upload own recordings" ON storage.objects;
CREATE POLICY "Users can upload own recordings"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'recordings'
    AND auth.uid()::text = (storage.foldername(name))[2]
  );

DROP POLICY IF EXISTS "Users can view own recordings" ON storage.objects;
CREATE POLICY "Users can view own recordings"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'recordings'
    AND auth.uid()::text = (storage.foldername(name))[2]
  );

-- Storage RLS policies for materials bucket
DROP POLICY IF EXISTS "Users can upload own materials" ON storage.objects;
CREATE POLICY "Users can upload own materials"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'materials'
    AND auth.uid()::text = (storage.foldername(name))[2]
  );

DROP POLICY IF EXISTS "Users can view own materials" ON storage.objects;
CREATE POLICY "Users can view own materials"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'materials'
    AND auth.uid()::text = (storage.foldername(name))[2]
  );

-- ============================================================================
-- 10. VERIFICATION QUERIES
-- ============================================================================
-- Run these after the migration to confirm everything was created successfully.
-- ============================================================================

-- Verify tables exist
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('profiles', 'sessions', 'answers', 'session_feedback', 'resumes')
ORDER BY table_name;

-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('profiles', 'sessions', 'answers', 'session_feedback', 'resumes');

-- Verify policies exist
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Verify indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Verify custom types
SELECT typname
FROM pg_type
WHERE typname IN ('session_type', 'interview_type', 'difficulty_level', 'session_status');

-- Verify storage bucket
SELECT id, name, public, file_size_limit
FROM storage.buckets
WHERE id = 'resumes';
