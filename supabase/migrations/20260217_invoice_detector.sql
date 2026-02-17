-- Invoice Duplicate Detector - Supabase Migration
-- Tables: invoices, duplicate_pairs

-- ============================================
-- Invoices
-- ============================================
CREATE TABLE IF NOT EXISTS invoices (
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

CREATE INDEX idx_invoices_account_id ON invoices(account_id);
CREATE INDEX idx_invoices_file_hash ON invoices(file_hash);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_vendor ON invoices(vendor_name);

-- ============================================
-- Duplicate Pairs
-- ============================================
CREATE TABLE IF NOT EXISTS duplicate_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(100) NOT NULL,
    invoice_a_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    invoice_b_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    similarity_score NUMERIC(6,4) NOT NULL,
    match_details JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'dismissed')),
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(invoice_a_id, invoice_b_id)
);

CREATE INDEX idx_dup_account ON duplicate_pairs(account_id);
CREATE INDEX idx_dup_status ON duplicate_pairs(status);
CREATE INDEX idx_dup_score ON duplicate_pairs(similarity_score DESC);

-- ============================================
-- RLS Policies
-- ============================================
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_pairs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on invoices"
    ON invoices FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on duplicate_pairs"
    ON duplicate_pairs FOR ALL
    USING (true)
    WITH CHECK (true);
