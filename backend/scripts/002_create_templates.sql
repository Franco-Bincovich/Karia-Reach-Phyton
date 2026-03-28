-- 002: Tabla templates — plantillas de email con asunto, cuerpo, tono y objetivo.
-- Ejecutar despues de 001. Sin dependencias FK.
CREATE TABLE IF NOT EXISTS templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT NOT NULL,
  asunto TEXT NOT NULL,
  cuerpo TEXT NOT NULL,
  tono TEXT DEFAULT '',
  objetivo TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
