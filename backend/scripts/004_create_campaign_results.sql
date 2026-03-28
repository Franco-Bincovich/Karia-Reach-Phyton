-- 004: Tabla campaign_results — resultado individual por email enviado.
-- Depende de: 001 (contacts) y 003 (campaigns) via FK.
CREATE TABLE IF NOT EXISTS campaign_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id),
  contact_id UUID REFERENCES contacts(id),
  email_destinatario TEXT,
  asunto TEXT,
  message_id TEXT,
  exitoso BOOLEAN DEFAULT FALSE,
  error TEXT,
  enviado_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_campaign_id ON campaign_results(campaign_id);
CREATE INDEX IF NOT EXISTS idx_results_contact_id ON campaign_results(contact_id);
CREATE INDEX IF NOT EXISTS idx_results_opened ON campaign_results(opened_at) WHERE opened_at IS NOT NULL;
