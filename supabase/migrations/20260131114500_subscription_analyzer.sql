-- Migration for Subscription Leak Detector tables
-- Created at: 2026-01-31

-- 1. Table: analyses
CREATE TABLE IF NOT EXISTS analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL, -- Assuming 'accounts' table exists, add REFERENCES accounts(id) if strict
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_account ON analyses(account_id);
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);

-- RLS for analyses
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Note: We assume a 'memberships' table exists mapping users to accounts. 
-- If not, simplify policy to: verify user_id = auth.uid()

CREATE POLICY "Users can view their account analyses"
  ON analyses FOR SELECT
  USING (
    account_id IN (
      SELECT account_id FROM memberships WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert analyses for their accounts"
  ON analyses FOR INSERT
  WITH CHECK (
    account_id IN (
      SELECT account_id FROM memberships WHERE user_id = auth.uid()
    )
  );
  
CREATE POLICY "Users can update their account analyses"
  ON analyses FOR UPDATE
  USING (
    account_id IN (
      SELECT account_id FROM memberships WHERE user_id = auth.uid()
    )
  );

-- 2. Table: analysis_items
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
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_analysis ON analysis_items(analysis_id);
CREATE INDEX IF NOT EXISTS idx_items_confidence ON analysis_items(confidence_score DESC);

-- RLS for analysis_items
ALTER TABLE analysis_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view items of their analyses"
  ON analysis_items FOR SELECT
  USING (
    analysis_id IN (
      SELECT id FROM analyses WHERE account_id IN (
        SELECT account_id FROM memberships WHERE user_id = auth.uid()
      )
    )
  );
