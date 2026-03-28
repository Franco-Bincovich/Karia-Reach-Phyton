-- 001: Tabla contacts — contactos comerciales (ai, manual, apollo).
-- Ejecutar primero. Sin dependencias FK.
CREATE TABLE IF NOT EXISTS contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT NOT NULL,
  empresa TEXT NOT NULL,
  cargo TEXT DEFAULT '',
  email_empresarial TEXT,
  email_personal TEXT,
  telefono_empresa TEXT,
  telefono_personal TEXT,
  confianza FLOAT DEFAULT 0.0,
  origen TEXT DEFAULT 'manual' CHECK (origen IN ('ai', 'manual', 'apollo')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_email_empresarial ON contacts(email_empresarial);
CREATE INDEX IF NOT EXISTS idx_contacts_email_personal ON contacts(email_personal);
