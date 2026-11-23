# AegisMind Supabase Integration Implementation Plan

## Overview
Integrate Supabase as the primary authentication and database backend for the existing Flask-based AegisMind application, preserving the existing UI, design, features, Flask architecture, and AI agent pipeline.

## Current State Analysis
- **Flask app** (`app.py`): Multi-agent pipeline (guard_agent, nlp_agent, trajectory_agent, crisis_agent, hitl_agent)
- **In-memory stores**: USER_PROFILES, CHECK_IN_HISTORY, FORUM_POSTS, COUNSELOR_QUEUE, SEV1_CASES, CHAT_SESSIONS
- **Auth**: Anonymous token-based login (`/api/register`, `/api/login`), Google OAuth with session storage
- **Database**: SQLAlchemy models in `models.py` (commented out, placeholder)
- **Frontend**: index.html, login.html, app.js, mobile.css, login.css
- **Environment**: `.env` with GOOGLE_CLIENT_ID/SECRET, GROQ_API_KEY, DATABASE_URL (not set)

## Integration Architecture

### 1. Supabase Setup
- Create Supabase project
- Configure Google OAuth in Supabase (client ID/secret from existing .env)
- Enable Email/Password authentication
- Get Supabase URL and anon key

### 2. Database Schema (PostgreSQL via Supabase)
Create tables with RLS:
- `profiles` - user profiles referencing Auth users (UUID)
- `check_ins` - wellness check-in records
- `chat_messages` - AI companion chat history
- `journal_entries` - reflective journal entries
- `counselor_cases` - HITL counselor case records
- `forum_posts` - community forum posts
- `audit_logs` - immutable audit trail

### 3. Flask Backend Changes
- Add Supabase Python SDK
- Verify Supabase JWTs on protected endpoints
- Replace in-memory dict operations with database queries
- Maintain all existing API functionality
- Add role-based access (user/counselor/admin)

### 4. Frontend Changes
- Add Supabase JavaScript client
- Connect login/register UI to Supabase
- Protected sessions via auth state
- Fetch user-specific data
- Remove localStorage token restoration

### 5. Persistent AI Memory
- Store/retrieve conversation history per user
- Maintain user-approved preferences/context
- Generate conversation summaries
- Supply context to AI companion
- Allow users to manage/delete memories

### 6. Google OAuth Integration
- "Continue with Google" button using Supabase Google OAuth
- Proper OAuth callbacks, session restoration, token refresh, logout

## Phase Gate Plan

### Phase 1: Supabase Project & Dependencies ✅
- [ ] Create Supabase project
- [ ] Configure Google OAuth
- [ ] Install Supabase Python JS SDKs
- [ ] Update requirements.txt

### Phase 2: Database Schema & RLS Policies ✅
- [ ] Create SQL migration files
- [ ] Implement RLS policies for all tables
- [ ] Test cross-user data isolation

### Phase 3: Flask Authentication Integration ✅
- [ ] Add Supabase JWT verification middleware
- [ ] Update /api/register, /api/login endpoints
- [ ] Implement Google OAuth callback via Supabase
- [ ] Implement logout, session persistence, token refresh
- [ ] Implement profile management and account deletion

### Phase 4: Database Operations Migration ✅
- [ ] Replace in-memory CHECK_IN_HISTORY with DB operations
- [ ] Replace in-memory CHAT_SESSIONS with DB operations
- [ ] Replace in-memory FORUM_POSTS with DB operations
- [ ] Replace in-memory USER_PROFILES with DB operations
- [ ] Update all API endpoints to use DB

### Phase 5: Frontend Integration ✅
- [ ] Integrate Supabase JS client
- [ ] Connect login/register UI to Supabase
- [ ] Add protected sessions and auth-aware navigation
- [ ] Fetch real user-specific check-in history and chat history
- [ ] Remove obsolete localStorage auth tokens

### Phase 6: Persistent AI Memory ✅
- [ ] Implement conversation history retrieval
- [ ] Maintain user-approved preferences
- [ ] Generate conversation summaries
- [ ] Supply context to AI companion
- [ ] Allow users to view/manage/delete memories

### Phase 7: Testing & Deployment ✅
- [ ] Automated tests for auth, authorization, DB access
- [ ] Google auth, persistent sessions, memory retrieval testing
- [ ] Cross-user data isolation verification
- [ ] Setup instructions