-- =============================================================================
-- AegisMind — Psychiatrist dashboard additions
-- =============================================================================
-- Run this once in the Supabase SQL editor, AFTER 20240101_01_initial_schema.sql.
-- It is safe to run twice (every step checks before changing anything).
--
-- What it does: the psychiatrist dashboard needs to know where a case came from
-- (check-in or chatbot) and how far the psychiatrist has got with it. Those four
-- fields are added to the existing counselor_cases table. No new table is needed.
-- =============================================================================

-- Where the case came from: 'checkin' or 'chat'
ALTER TABLE counselor_cases ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'checkin';

-- Progress of the case: new -> acknowledged -> in_contact -> resolved
ALTER TABLE counselor_cases ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'new';

-- Private note written by the psychiatrist
ALTER TABLE counselor_cases ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT '';

-- First time a psychiatrist picked the case up
ALTER TABLE counselor_cases ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ;

-- Only the four known statuses are allowed
ALTER TABLE counselor_cases DROP CONSTRAINT IF EXISTS counselor_cases_status_check;
ALTER TABLE counselor_cases ADD CONSTRAINT counselor_cases_status_check
    CHECK (status IN ('new', 'acknowledged', 'in_contact', 'resolved'));

-- Cases that were already reviewed before this migration count as resolved
UPDATE counselor_cases SET status = 'resolved' WHERE reviewed = TRUE AND status = 'new';

-- Speeds up the dashboard's "open cases, SEV-1 first, newest first" list
CREATE INDEX IF NOT EXISTS idx_counselorcases_open_priority
    ON counselor_cases (reviewed, sev, flagged_at DESC);

CREATE INDEX IF NOT EXISTS idx_counselorcases_status ON counselor_cases (status);

-- Row Level Security: nothing new is needed. The server talks to Supabase with the
-- service role key, which already has the "Counselors can view all cases" access
-- from the initial schema, and patients still cannot read counselor_cases.
