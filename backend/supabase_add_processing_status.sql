-- Add 'processing' to the session_status enum type
-- Run this in your Supabase SQL Editor

ALTER TYPE session_status ADD VALUE IF NOT EXISTS 'processing';
