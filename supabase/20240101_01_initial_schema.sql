-- =============================================================================
-- AegisMind — Initial PostgreSQL Schema for Supabase
-- =============================================================================
-- This migration creates all required tables with RLS-enabled security.
-- All tables use UUID user IDs referencing Supabase Auth users.
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Table: profiles
-- User profiles referencing Supabase Auth users.
-- =============================================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    alias TEXT,
    theme_preference TEXT DEFAULT 'dark',
    language_preference TEXT DEFAULT 'en',
    consent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for lookups by user_id
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);

-- =============================================================================
-- Table: check_ins
-- Wellness check-in records with NLP analysis results.
-- =============================================================================
CREATE TABLE IF NOT EXISTS check_ins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    valence FLOAT NOT NULL,
    arousal FLOAT NOT NULL,
    voice_score FLOAT DEFAULT 0.7,
    nlp_json JSONB,
    dpi FLOAT,
    delta_dpi FLOAT,
    risk_level TEXT,  -- low / moderate / critical
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for check-in queries
CREATE INDEX IF NOT EXISTS idx_checkins_user_id ON check_ins(user_id);
CREATE INDEX IF NOT EXISTS idx_checkins_risk_level ON check_ins(risk_level);
CREATE INDEX IF NOT EXISTS idx_checkins_created_at ON check_ins(created_at DESC);

-- =============================================================================
-- Table: chat_messages
-- AI companion chat message history for persistent conversational memory.
-- =============================================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    sender TEXT NOT NULL,  -- 'user' or 'companion'
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for chat history queries
CREATE INDEX IF NOT EXISTS idx_chatmessages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chatmessages_created_at ON chat_messages(created_at DESC);

-- =============================================================================
-- Table: journal_entries
-- Reflective journal entries submitted by users.
-- =============================================================================
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT,
    text TEXT NOT NULL,
    valence FLOAT,
    arousal FLOAT,
    voice_score FLOAT DEFAULT 0.7,
    nlp_json JSONB,
    dpi FLOAT,
    delta_dpi FLOAT,
    risk_level TEXT,  -- low / moderate / critical
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for journal queries
CREATE INDEX IF NOT EXISTS idx_journalentries_user_id ON journal_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_journalentries_created_at ON journal_entries(created_at DESC);

-- =============================================================================
-- Table: counselor_cases
-- HITL counselor review queue entries.
-- =============================================================================
CREATE TABLE IF NOT EXISTS counselor_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    alias TEXT,
    dpi FLOAT NOT NULL,
    delta_dpi FLOAT NOT NULL,
    risk_level TEXT NOT NULL,  -- low / moderate / critical
    triggers JSONB DEFAULT '[]',
    text_fragment TEXT,
    jitsi_room TEXT,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMPTZ,
    sev TEXT DEFAULT 'SEV-2',  -- SEV-1 or SEV-2
    flagged_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for counselor queue queries
CREATE INDEX IF NOT EXISTS idx_counselorcases_user_id ON counselor_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_counselorcases_reviewed ON counselor_cases(reviewed);
CREATE INDEX IF NOT EXISTS idx_counselorcases_flagged_at ON counselor_cases(flagged_at DESC);

-- =============================================================================
-- Table: forum_posts
-- Anonymous community forum posts with moderation state.
-- Users can post anonymously or with their profile alias.
-- =============================================================================
CREATE TABLE IF NOT EXISTS forum_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    alias TEXT,
    text TEXT NOT NULL,
    lang TEXT DEFAULT 'en',
    reactions JSONB DEFAULT '{"heart": 0, "hug": 0, "star": 0}',
    flagged BOOLEAN DEFAULT FALSE,
    reports INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for forum queries
CREATE INDEX IF NOT EXISTS idx_forumposts_flagged ON forum_posts(flagged);
CREATE INDEX IF NOT EXISTS idx_forumposts_created_at ON forum_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_forumposts_user_id ON forum_posts(user_id);

-- =============================================================================
-- Table: audit_logs
-- Immutable audit trail for compliance with HIPAA/India DPDP Act.
-- Written automatically on critical events.
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    target_id TEXT,
    details JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for audit log queries
CREATE INDEX IF NOT EXISTS idx_auditlogs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_auditlogs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auditlogs_user_id ON audit_logs(user_id);

-- =============================================================================
-- Row Level Security (RLS) Policies
-- =============================================================================
-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE check_ins ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE counselor_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Profiles policies
-- Users can view their own profile; admins can view all
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all profiles" ON profiles
    FOR ALL USING (auth.role() = 'service_role');

-- Check-in policies
-- Users can view/create their own check-ins
CREATE POLICY "Users can view own check-ins" ON check_ins
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own check-ins" ON check_ins
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins can view all check-ins" ON check_ins
    FOR SELECT USING (auth.role() = 'service_role');

-- Chat message policies
-- Users can view their own chat messages
CREATE POLICY "Users can view own chat messages" ON chat_messages
    FOR SELECT USING (auth.uid() = user_id);

-- Journal entry policies
-- Users can view/create their own journal entries
CREATE POLICY "Users can view own journal entries" ON journal_entries
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own journal entries" ON journal_entries
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins can view all journal entries" ON journal_entries
    FOR SELECT USING (auth.role() = 'service_role');

-- Counselor case policies
-- Counselors/admins can view all cases
CREATE POLICY "Counselors can view all cases" ON counselor_cases
    FOR SELECT USING (auth.role() = 'service_role');

-- Forum post policies
-- Users can view their own posts and public (non-flagged) posts
CREATE POLICY "Users can view own forum posts" ON forum_posts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Anyone can view non-flagged forum posts" ON forum_posts
    FOR SELECT USING (flagged = FALSE);

CREATE POLICY "Users can insert own forum posts" ON forum_posts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins can view all forum posts" ON forum_posts
    FOR SELECT USING (auth.role() = 'service_role');

-- Audit log policies
-- Admins can view all audit logs
CREATE POLICY "Admins can view all audit logs" ON audit_logs
    FOR SELECT USING (auth.role() = 'service_role');