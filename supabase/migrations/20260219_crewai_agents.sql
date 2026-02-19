-- CrewAI Agents Service - Database Schema
-- Tables for agent settings, notifications, tax obligations, financial insights, etc.

-- ============================================
-- 1. Business Profiles
-- ============================================
CREATE TABLE IF NOT EXISTS business_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    business_type TEXT NOT NULL CHECK (business_type IN (
        'micro_entrepreneur', 'sarl', 'sas', 'sasu', 'ei', 'eurl', 'other'
    )),
    tax_regime TEXT NOT NULL DEFAULT 'micro' CHECK (tax_regime IN (
        'micro', 'reel_simplifie', 'reel_normal'
    )),
    declaration_frequency TEXT NOT NULL DEFAULT 'monthly' CHECK (declaration_frequency IN (
        'monthly', 'quarterly'
    )),
    tva_applicable BOOLEAN NOT NULL DEFAULT FALSE,
    siret TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id)
);

-- ============================================
-- 2. Agent Settings
-- ============================================
CREATE TABLE IF NOT EXISTS agent_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    agent_type TEXT NOT NULL CHECK (agent_type IN (
        'financial_assistant', 'tax_assistant', 'document_manager',
        'client_assistant', 'operations_coordinator'
    )),
    status TEXT NOT NULL DEFAULT 'disabled' CHECK (status IN ('enabled', 'disabled')),
    notification_channels JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, agent_type)
);

-- ============================================
-- 3. Tax Obligations
-- ============================================
CREATE TABLE IF NOT EXISTS tax_obligations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    obligation_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    deadline TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'reminded', 'completed', 'overdue'
    )),
    draft_data JSONB,
    service_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. Financial Insights
-- ============================================
CREATE TABLE IF NOT EXISTS financial_insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    insight_type TEXT NOT NULL CHECK (insight_type IN (
        'anomaly', 'trend', 'subscription', 'recommendation'
    )),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN (
        'info', 'warning', 'critical'
    )),
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. Document Links
-- ============================================
CREATE TABLE IF NOT EXISTS document_links (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    document_id UUID NOT NULL,
    transaction_id TEXT,
    match_confidence FLOAT,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 6. Agent Execution Logs
-- ============================================
CREATE TABLE IF NOT EXISTS agent_execution_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    flow_name TEXT,
    trigger TEXT,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN (
        'running', 'completed', 'failed'
    )),
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- 7. Agent Notifications (in-app)
-- ============================================
CREATE TABLE IF NOT EXISTS agent_notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT NOT NULL DEFAULT 'info' CHECK (notification_type IN (
        'info', 'warning', 'action_required', 'success'
    )),
    agent_type TEXT,
    action_url TEXT,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 8. Weekly Reports
-- ============================================
CREATE TABLE IF NOT EXISTS weekly_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    financial_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_business_profiles_account ON business_profiles(account_id);
CREATE INDEX IF NOT EXISTS idx_agent_settings_account ON agent_settings(account_id);
CREATE INDEX IF NOT EXISTS idx_agent_settings_account_type ON agent_settings(account_id, agent_type);
CREATE INDEX IF NOT EXISTS idx_tax_obligations_account ON tax_obligations(account_id);
CREATE INDEX IF NOT EXISTS idx_tax_obligations_deadline ON tax_obligations(deadline);
CREATE INDEX IF NOT EXISTS idx_tax_obligations_status ON tax_obligations(account_id, status);
CREATE INDEX IF NOT EXISTS idx_financial_insights_account ON financial_insights(account_id);
CREATE INDEX IF NOT EXISTS idx_financial_insights_unack ON financial_insights(account_id, acknowledged);
CREATE INDEX IF NOT EXISTS idx_document_links_account ON document_links(account_id);
CREATE INDEX IF NOT EXISTS idx_document_links_document ON document_links(document_id);
CREATE INDEX IF NOT EXISTS idx_agent_execution_logs_account ON agent_execution_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_agent_execution_logs_flow ON agent_execution_logs(account_id, flow_name);
CREATE INDEX IF NOT EXISTS idx_agent_notifications_account ON agent_notifications(account_id);
CREATE INDEX IF NOT EXISTS idx_agent_notifications_unread ON agent_notifications(account_id, read);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_account ON weekly_reports(account_id);

-- ============================================
-- Row Level Security (RLS)
-- ============================================
ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_obligations ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_execution_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies: service role has full access
CREATE POLICY "Service role full access on business_profiles"
    ON business_profiles FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on agent_settings"
    ON agent_settings FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on tax_obligations"
    ON tax_obligations FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on financial_insights"
    ON financial_insights FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on document_links"
    ON document_links FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on agent_execution_logs"
    ON agent_execution_logs FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on agent_notifications"
    ON agent_notifications FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on weekly_reports"
    ON weekly_reports FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================
-- Updated_at trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_business_profiles_updated_at
    BEFORE UPDATE ON business_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_settings_updated_at
    BEFORE UPDATE ON agent_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tax_obligations_updated_at
    BEFORE UPDATE ON tax_obligations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
