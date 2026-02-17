-- Team Reminder Bot - Supabase Migration
-- Tables: teams, reminders, context_history

-- ============================================
-- Teams
-- ============================================
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slack_team_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    subscription_tier VARCHAR(20) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'starter', 'pro')),
    reminders_count INTEGER DEFAULT 0,
    max_reminders INTEGER DEFAULT 50,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_teams_slack_team_id ON teams(slack_team_id);

-- ============================================
-- Reminders
-- ============================================
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    creator_user_id VARCHAR(100) NOT NULL,
    target_user_id VARCHAR(100) NOT NULL,
    task_text TEXT NOT NULL,
    context TEXT,
    project VARCHAR(200),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    remind_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'completed', 'cancelled', 'failed', 'snoozed')),
    repeat VARCHAR(20) CHECK (repeat IS NULL OR repeat IN ('daily', 'weekly', 'biweekly', 'monthly')),
    parent_reminder_id UUID REFERENCES reminders(id) ON DELETE SET NULL,
    sent_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    snooze_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_reminders_team_id ON reminders(team_id);
CREATE INDEX idx_reminders_status ON reminders(status);
CREATE INDEX idx_reminders_remind_at ON reminders(remind_at);
CREATE INDEX idx_reminders_target_user ON reminders(target_user_id);
CREATE INDEX idx_reminders_due ON reminders(status, remind_at) WHERE status = 'pending';

-- ============================================
-- Context History
-- ============================================
CREATE TABLE IF NOT EXISTS context_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    related_reminder_id UUID REFERENCES reminders(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_context_history_team_user ON context_history(team_id, user_id);
CREATE INDEX idx_context_history_created ON context_history(created_at DESC);

-- ============================================
-- RLS Policies (Row Level Security)
-- ============================================
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_history ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (for backend API)
CREATE POLICY "Service role full access on teams"
    ON teams FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on reminders"
    ON reminders FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on context_history"
    ON context_history FOR ALL
    USING (true)
    WITH CHECK (true);
