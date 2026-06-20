-- =============================================================================
-- SimplifyEU consolidated application schema (Phase 2: Supabase -> plain Postgres)
-- =============================================================================
-- Single source of truth for the app schema on plain PostgreSQL.
-- Consolidated from supabase/migrations/*.sql, taking the latest / most-complete
-- definition of each object. Supabase-specific bits (auth schema, RLS, policies,
-- GRANTs to anon/authenticated/service_role, storage buckets) are intentionally
-- stripped: RLS is Phase 5, Better Auth tables are Phase 3.
--
-- FK repointing:
--   * app `users.id` was `references auth.users(id)` -> now self-owned
--     (default gen_random_uuid()). It is the canonical user row for now.
--   * every other `references auth.users(id)` -> `references users(id)`.
--
-- Requires the pgcrypto extension for gen_random_uuid() (installed).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- ENUMS  (idempotent via DO guards)
-- =============================================================================

DO $$ BEGIN
  CREATE TYPE account_type AS ENUM ('personal', 'company');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE api_key_type AS ENUM ('standard', 'admin', 'read-only');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE api_key_status AS ENUM ('active', 'revoked', 'expired');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE audit_action AS ENUM (
    'account_created', 'account_updated', 'account_deleted',
    'user_invited', 'user_removed', 'role_changed',
    'subscription_created', 'subscription_updated', 'subscription_canceled',
    'invoice_created', 'invoice_sent', 'invoice_paid', 'invoice_voided',
    'api_key_created', 'api_key_revoked',
    'service_added', 'service_removed', 'service_updated',
    'settings_updated', 'password_changed', 'email_changed',
    'login_success', 'login_failed', 'logout',
    'webhook_triggered', 'webhook_failed'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notification_type AS ENUM (
    'invoice_created', 'invoice_paid', 'invoice_overdue',
    'subscription_created', 'subscription_renewed', 'subscription_canceled', 'subscription_trial_ending',
    'payment_succeeded', 'payment_failed', 'payment_method_expiring',
    'account_invitation', 'account_role_changed',
    'service_added', 'service_removed',
    'api_key_created', 'api_key_expiring', 'api_key_revoked',
    'system_announcement', 'security_alert'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notification_status AS ENUM ('unread', 'read', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE webhook_status AS ENUM ('pending', 'success', 'failed', 'retrying');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
-- updated_at trigger function
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- =============================================================================
-- CORE TABLES (billing / accounts)
-- =============================================================================

-- Users (was: references auth.users(id); now canonical, self-owned).
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  type account_type NOT NULL,
  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  stripe_customer_id TEXT UNIQUE,
  vat_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  UNIQUE (account_id, user_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  stripe_subscription_id TEXT UNIQUE,
  plan TEXT NOT NULL DEFAULT 'free',
  status TEXT NOT NULL DEFAULT 'active',
  current_period_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  current_period_end TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  cancel_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Core billing invoices (Stripe-linked). NOTE: distinct from the invoice-detector
-- table, which is consolidated below as `detector_invoices` to avoid a name clash.
CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  stripe_invoice_id TEXT UNIQUE,
  amount NUMERIC NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'eur',
  status TEXT NOT NULL DEFAULT 'draft',
  pdf_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  icon TEXT,
  pricing_type TEXT NOT NULL DEFAULT 'included',
  addon_price NUMERIC,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  prefix TEXT NOT NULL,
  hashed_key TEXT NOT NULL,
  type api_key_type NOT NULL DEFAULT 'standard',
  status api_key_status NOT NULL DEFAULT 'active',
  last_used_at TIMESTAMP WITH TIME ZONE,
  expires_at TIMESTAMP WITH TIME ZONE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action audit_action NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  old_data JSONB,
  new_data JSONB,
  ip_address INET,
  user_agent TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
  type notification_type NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  data JSONB DEFAULT '{}',
  status notification_status NOT NULL DEFAULT 'unread',
  read_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webhook_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  webhook_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  url TEXT NOT NULL,
  status webhook_status NOT NULL DEFAULT 'pending',
  response_status INTEGER,
  response_body TEXT,
  error_message TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 1,
  next_retry_at TIMESTAMP WITH TIME ZONE,
  last_attempt_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 1,
  bandwidth_bytes BIGINT NOT NULL DEFAULT 0,
  period_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT date_trunc('day', now()),
  period_end TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT date_trunc('day', now()) + INTERVAL '1 day',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- =============================================================================
-- SUBSCRIPTION ANALYZER
-- Reconciled from 3 source files; most-complete variant: FK to accounts(id),
-- FK to users(id) (was auth.users), and the CHECK constraints.
-- =============================================================================

CREATE TABLE IF NOT EXISTS analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  source_type TEXT NOT NULL DEFAULT 'csv',
  filename TEXT,
  file_url TEXT,
  total_transactions INTEGER,
  subscriptions_found INTEGER DEFAULT 0,
  potential_savings_eur DECIMAL(10,2) DEFAULT 0,
  report_url TEXT,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  merchant_descriptor TEXT NOT NULL,
  merchant_name TEXT,
  category TEXT,
  amount_avg DECIMAL(10,2) NOT NULL,
  amount_min DECIMAL(10,2),
  amount_max DECIMAL(10,2),
  currency TEXT DEFAULT 'EUR',
  frequency TEXT CHECK (frequency IN ('weekly', 'biweekly', 'monthly', 'quarterly', 'annual', 'irregular')),
  occurrences INTEGER NOT NULL,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL,
  confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
  is_subscription BOOLEAN DEFAULT FALSE,
  tags JSONB DEFAULT '[]'::jsonb,
  recommendation TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- INVOICE DUPLICATE DETECTOR
-- The source named this table `invoices`, which collides with the core billing
-- `invoices` above. Renamed to `detector_invoices` here so both survive.
-- account_id is a free-form VARCHAR tenant key in the source (not an FK).
-- =============================================================================

CREATE TABLE IF NOT EXISTS detector_invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id VARCHAR(100) NOT NULL,
  filename VARCHAR(500) NOT NULL,
  file_hash VARCHAR(64) NOT NULL,
  invoice_number VARCHAR(100),
  vendor_name VARCHAR(300),
  invoice_date VARCHAR(20),
  due_date VARCHAR(20),
  total_amount NUMERIC(15,2),
  currency VARCHAR(10) DEFAULT 'EUR',
  line_items JSONB DEFAULT '[]',
  raw_text TEXT,
  ocr_used BOOLEAN DEFAULT false,
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'error')),
  processing_error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS duplicate_pairs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id VARCHAR(100) NOT NULL,
  invoice_a_id UUID NOT NULL REFERENCES detector_invoices(id) ON DELETE CASCADE,
  invoice_b_id UUID NOT NULL REFERENCES detector_invoices(id) ON DELETE CASCADE,
  similarity_score NUMERIC(6,4) NOT NULL,
  match_details JSONB DEFAULT '{}',
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'dismissed')),
  reviewed_by VARCHAR(100),
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (invoice_a_id, invoice_b_id)
);

-- =============================================================================
-- TEAM REMINDER BOT
-- =============================================================================

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

CREATE TABLE IF NOT EXISTS context_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  user_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  event_data JSONB DEFAULT '{}',
  related_reminder_id UUID REFERENCES reminders(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- CREWAI AGENTS SERVICE
-- account_id is a free-form TEXT tenant key in the source (not an FK).
-- =============================================================================

CREATE TABLE IF NOT EXISTS business_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (account_id)
);

CREATE TABLE IF NOT EXISTS agent_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id TEXT NOT NULL,
  agent_type TEXT NOT NULL CHECK (agent_type IN (
    'financial_assistant', 'tax_assistant', 'document_manager',
    'client_assistant', 'operations_coordinator'
  )),
  status TEXT NOT NULL DEFAULT 'disabled' CHECK (status IN ('enabled', 'disabled')),
  notification_channels JSONB NOT NULL DEFAULT '["in_app"]'::jsonb,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (account_id, agent_type)
);

CREATE TABLE IF NOT EXISTS tax_obligations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financial_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id TEXT NOT NULL,
  document_id UUID NOT NULL,
  transaction_id TEXT,
  match_confidence FLOAT,
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_execution_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS agent_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id TEXT NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  notification_type TEXT NOT NULL DEFAULT 'info' CHECK (notification_type IN (
    'info', 'warning', 'action_required', 'success'
  )),
  agent_type TEXT,
  action_url TEXT,
  read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS weekly_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id TEXT NOT NULL,
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  summary TEXT NOT NULL,
  highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
  action_items JSONB NOT NULL DEFAULT '[]'::jsonb,
  financial_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Core
CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);

CREATE INDEX IF NOT EXISTS idx_accounts_owner_id ON accounts(owner_id);
CREATE INDEX IF NOT EXISTS idx_accounts_stripe_customer ON accounts(stripe_customer_id);

CREATE INDEX IF NOT EXISTS idx_memberships_account_id ON memberships(account_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user_id ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_memberships_role ON memberships(role);

CREATE INDEX IF NOT EXISTS idx_subscriptions_account_id ON subscriptions(account_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

CREATE INDEX IF NOT EXISTS idx_invoices_account_id ON invoices(account_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_stripe ON invoices(stripe_invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_services_slug ON services(slug);
CREATE INDEX IF NOT EXISTS idx_services_active ON services(is_active);

CREATE INDEX IF NOT EXISTS idx_api_keys_account_id ON api_keys(account_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_logs_account_id ON audit_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_account_created ON audit_logs(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_account_id ON notifications(account_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, status) WHERE status = 'unread';

CREATE INDEX IF NOT EXISTS idx_webhook_logs_account_id ON webhook_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_status ON webhook_logs(status);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_event_type ON webhook_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_next_retry ON webhook_logs(next_retry_at) WHERE status = 'retrying';
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_usage_api_key_id ON api_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_account_id ON api_usage(account_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_period ON api_usage(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_api_usage_key_period ON api_usage(api_key_id, period_start DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_usage_unique ON api_usage(api_key_id, period_start, endpoint);

-- Subscription analyzer
CREATE INDEX IF NOT EXISTS idx_analyses_account ON analyses(account_id);
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);
CREATE INDEX IF NOT EXISTS idx_items_analysis ON analysis_items(analysis_id);
CREATE INDEX IF NOT EXISTS idx_items_confidence ON analysis_items(confidence_score DESC);

-- Invoice detector
CREATE INDEX IF NOT EXISTS idx_invoices_account_id_det ON detector_invoices(account_id);
CREATE INDEX IF NOT EXISTS idx_invoices_file_hash ON detector_invoices(file_hash);
CREATE INDEX IF NOT EXISTS idx_invoices_status_det ON detector_invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON detector_invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_vendor ON detector_invoices(vendor_name);
CREATE INDEX IF NOT EXISTS idx_dup_account ON duplicate_pairs(account_id);
CREATE INDEX IF NOT EXISTS idx_dup_status ON duplicate_pairs(status);
CREATE INDEX IF NOT EXISTS idx_dup_score ON duplicate_pairs(similarity_score DESC);

-- Team reminder bot
CREATE INDEX IF NOT EXISTS idx_teams_slack_team_id ON teams(slack_team_id);
CREATE INDEX IF NOT EXISTS idx_reminders_team_id ON reminders(team_id);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at);
CREATE INDEX IF NOT EXISTS idx_reminders_target_user ON reminders(target_user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(status, remind_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_context_history_team_user ON context_history(team_id, user_id);
CREATE INDEX IF NOT EXISTS idx_context_history_created ON context_history(created_at DESC);

-- CrewAI agents
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

-- =============================================================================
-- updated_at TRIGGERS
-- =============================================================================

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_accounts_updated_at ON accounts;
CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_api_keys_updated_at ON api_keys;
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_analyses_updated_at ON analyses;
CREATE TRIGGER update_analyses_updated_at BEFORE UPDATE ON analyses
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_detector_invoices_updated_at ON detector_invoices;
CREATE TRIGGER update_detector_invoices_updated_at BEFORE UPDATE ON detector_invoices
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_teams_updated_at ON teams;
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_reminders_updated_at ON reminders;
CREATE TRIGGER update_reminders_updated_at BEFORE UPDATE ON reminders
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_business_profiles_updated_at ON business_profiles;
CREATE TRIGGER update_business_profiles_updated_at BEFORE UPDATE ON business_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_settings_updated_at ON agent_settings;
CREATE TRIGGER update_agent_settings_updated_at BEFORE UPDATE ON agent_settings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tax_obligations_updated_at ON tax_obligations;
CREATE TRIGGER update_tax_obligations_updated_at BEFORE UPDATE ON tax_obligations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
