-- Tabla para almacenar API keys de servicios externos
CREATE TABLE IF NOT EXISTS integraciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  servicio TEXT UNIQUE NOT NULL,
  api_key TEXT NOT NULL,
  activo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice para busqueda por servicio activo
CREATE INDEX IF NOT EXISTS idx_integraciones_servicio_activo
  ON integraciones(servicio) WHERE activo = TRUE;
