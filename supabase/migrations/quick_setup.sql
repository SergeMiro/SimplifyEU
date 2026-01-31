-- Quick setup for Subscription Analyzer (No RLS complexities)

-- 1. Create Analyses Table
CREATE TABLE IF NOT EXISTS analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL,
  user_id UUID NOT NULL,
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

-- 2. Create Items Table
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
  frequency TEXT,
  occurrences INTEGER NOT NULL,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL,
  confidence_score DECIMAL(3,2),
  is_subscription BOOLEAN DEFAULT FALSE,
  tags JSONB DEFAULT '[]'::jsonb,
  recommendation TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Enable Public Access (TEMPORARY FOR TESTING)
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow All Access" ON analyses FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow All Access Items" ON analysis_items FOR ALL USING (true) WITH CHECK (true);

-- 4. Create Storage Buckets
INSERT INTO storage.buckets (id, name, public) 
VALUES ('uploads', 'uploads', false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO storage.buckets (id, name, public) 
VALUES ('reports', 'reports', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow uploads" ON storage.objects FOR ALL USING ( bucket_id = 'uploads' ) WITH CHECK ( bucket_id = 'uploads' );
CREATE POLICY "Allow reports" ON storage.objects FOR ALL USING ( bucket_id = 'reports' ) WITH CHECK ( bucket_id = 'reports' );
