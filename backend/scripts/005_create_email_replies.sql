-- Tabla para almacenar respuestas a emails de campanas
CREATE TABLE IF NOT EXISTS email_replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id),
  contact_id UUID REFERENCES contacts(id),
  message_id TEXT,
  in_reply_to TEXT,
  de TEXT NOT NULL,
  asunto TEXT,
  cuerpo TEXT,
  fecha TIMESTAMPTZ DEFAULT NOW(),
  leido BOOLEAN DEFAULT FALSE,
  respondido BOOLEAN DEFAULT FALSE
);

-- Indices para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_replies_campaign_id ON email_replies(campaign_id);
CREATE INDEX IF NOT EXISTS idx_replies_message_id ON email_replies(message_id);
CREATE INDEX IF NOT EXISTS idx_replies_leido ON email_replies(leido) WHERE leido = FALSE;
