-- Migration: Add Supabase database schema for SimplifyEU
-- Created: 2025-01-18
-- Description: Creates all application tables, enums, indexes, and RLS policies

-- =============================================================================
-- ENUMS
-- =============================================================================

-- Account type enum
CREATE TYPE account_type AS ENUM ('personal', 'company');

-- API key type enum
CREATE TYPE api_key_type AS ENUM ('standard', 'admin', 'read-only');

-- API key status enum
CREATE TYPE api_key_status AS ENUM ('active', 'revoked', 'expired');

-- Audit action enum
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

-- Notification type enum
CREATE TYPE notification_type AS ENUM (
  'invoice_created', 'invoice_paid', 'invoice_overdue',
  'subscription_created', 'subscription_renewed', 'subscription_canceled', 'subscription_trial_ending',
  'payment_succeeded', 'payment_failed', 'payment_method_expiring',
  'account_invitation', 'account_role_changed',
  'service_added', 'service_removed',
  'api_key_created', 'api_key_expiring', 'api_key_revoked',
  'system_announcement', 'security_alert'
);

-- Notification status enum
CREATE TYPE notification_status AS ENUM ('unread', 'read', 'archived');

-- Webhook status enum
CREATE TYPE webhook_status AS ENUM ('pending', 'success', 'failed', 'retrying');

-- =============================================================================
-- TABLES
-- =============================================================================

-- Users table (extends auth.users)
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Accounts table
CREATE TABLE accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  type account_type NOT NULL,
  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  stripe_customer_id TEXT UNIQUE,
  vat_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Memberships table (user-account relationship)
CREATE TABLE memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  UNIQUE(account_id, user_id)
);

-- Subscriptions table
CREATE TABLE subscriptions (
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

-- Invoices table
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  stripe_invoice_id TEXT UNIQUE,
  amount NUMERIC NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'eur',
  status TEXT NOT NULL DEFAULT 'draft',
  pdf_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Services table
CREATE TABLE services (
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

-- API Keys table
CREATE TABLE api_keys (
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

-- Audit Logs table
CREATE TABLE audit_logs (
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

-- Notifications table
CREATE TABLE notifications (
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

-- Webhook Logs table
CREATE TABLE webhook_logs (
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

-- API Usage table
CREATE TABLE api_usage (
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
-- INDEXES
-- =============================================================================

-- Users indexes
CREATE INDEX idx_users_id ON users(id);

-- Accounts indexes
CREATE INDEX idx_accounts_owner_id ON accounts(owner_id);
CREATE INDEX idx_accounts_stripe_customer ON accounts(stripe_customer_id);

-- Memberships indexes
CREATE INDEX idx_memberships_account_id ON memberships(account_id);
CREATE INDEX idx_memberships_user_id ON memberships(user_id);
CREATE INDEX idx_memberships_role ON memberships(role);

-- Subscriptions indexes
CREATE INDEX idx_subscriptions_account_id ON subscriptions(account_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

-- Invoices indexes
CREATE INDEX idx_invoices_account_id ON invoices(account_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_stripe ON invoices(stripe_invoice_id);
CREATE INDEX idx_invoices_created_at ON invoices(created_at DESC);

-- Services indexes
CREATE INDEX idx_services_slug ON services(slug);
CREATE INDEX idx_services_active ON services(is_active);

-- API Keys indexes
CREATE INDEX idx_api_keys_account_id ON api_keys(account_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(prefix);
CREATE INDEX idx_api_keys_status ON api_keys(status);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- Audit Logs indexes
CREATE INDEX idx_audit_logs_account_id ON audit_logs(account_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_account_created ON audit_logs(account_id, created_at DESC);

-- Notifications indexes
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_account_id ON notifications(account_id);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, status) WHERE status = 'unread';

-- Webhook Logs indexes
CREATE INDEX idx_webhook_logs_account_id ON webhook_logs(account_id);
CREATE INDEX idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
CREATE INDEX idx_webhook_logs_status ON webhook_logs(status);
CREATE INDEX idx_webhook_logs_event_type ON webhook_logs(event_type);
CREATE INDEX idx_webhook_logs_next_retry ON webhook_logs(next_retry_at) WHERE status = 'retrying';
CREATE INDEX idx_webhook_logs_created_at ON webhook_logs(created_at DESC);

-- API Usage indexes
CREATE INDEX idx_api_usage_api_key_id ON api_usage(api_key_id);
CREATE INDEX idx_api_usage_account_id ON api_usage(account_id);
CREATE INDEX idx_api_usage_period ON api_usage(period_start, period_end);
CREATE INDEX idx_api_usage_key_period ON api_usage(api_key_id, period_start DESC);
CREATE UNIQUE INDEX idx_api_usage_unique ON api_usage(api_key_id, period_start, endpoint);

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;

-- Users RLS
CREATE POLICY "Users can view own profile" ON users
  FOR SELECT USING (id = auth.uid());

CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE USING (id = auth.uid());

-- Accounts RLS
CREATE POLICY "Account owners can view their accounts" ON accounts
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = accounts.id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create accounts" ON accounts
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Account admins can update accounts" ON accounts
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = accounts.id
      AND memberships.user_id = auth.uid()
      AND memberships.role IN ('owner', 'admin')
    )
  );

-- Memberships RLS
CREATE POLICY "Users can view their memberships" ON memberships
  FOR SELECT USING (
    user_id = auth.uid() OR
    EXISTS (
      SELECT 1 FROM memberships m2
      WHERE m2.account_id = memberships.account_id
      AND m2.user_id = auth.uid()
      AND m2.role IN ('owner', 'admin')
    )
  );

CREATE POLICY "Account admins can manage memberships" ON memberships
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM memberships m2
      WHERE m2.account_id = memberships.account_id
      AND m2.user_id = auth.uid()
      AND m2.role IN ('owner', 'admin')
    )
  );

-- Subscriptions RLS
CREATE POLICY "Account members can view subscriptions" ON subscriptions
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = subscriptions.account_id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "Account admins can manage subscriptions" ON subscriptions
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = subscriptions.account_id
      AND memberships.user_id = auth.uid()
      AND memberships.role IN ('owner', 'admin')
    )
  );

-- Invoices RLS
CREATE POLICY "Account members can view invoices" ON invoices
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = invoices.account_id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "Account admins can manage invoices" ON invoices
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = invoices.account_id
      AND memberships.user_id = auth.uid()
      AND memberships.role IN ('owner', 'admin')
    )
  );

-- Services RLS
CREATE POLICY "Anyone can view active services" ON services
  FOR SELECT USING (is_active = true);

CREATE POLICY "Account admins can manage services" ON services
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = services.id
      AND memberships.user_id = auth.uid()
      AND memberships.role IN ('owner', 'admin')
    )
  );

-- API Keys RLS
CREATE POLICY "Account members can view api_keys" ON api_keys
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = api_keys.account_id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "Account admins can manage api_keys" ON api_keys
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = api_keys.account_id
      AND memberships.user_id = auth.uid()
      AND memberships.role IN ('owner', 'admin')
    )
  );

-- Audit Logs RLS
CREATE POLICY "Account members can view audit_logs" ON audit_logs
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = audit_logs.account_id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "System can insert audit_logs" ON audit_logs
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Notifications RLS
CREATE POLICY "Users can view their own notifications" ON notifications
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can update their own notifications" ON notifications
  FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "System can create notifications" ON notifications
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Webhook Logs RLS
CREATE POLICY "Account members can view webhook_logs" ON webhook_logs
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = webhook_logs.account_id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "System can insert webhook_logs" ON webhook_logs
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- API Usage RLS
CREATE POLICY "Account members can view api_usage" ON api_usage
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships
      WHERE memberships.account_id = api_usage.account_id
      AND memberships.user_id = auth.uid()
    )
  );

CREATE POLICY "System can manage api_usage" ON api_usage
  FOR ALL USING (auth.uid() IS NOT NULL);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();