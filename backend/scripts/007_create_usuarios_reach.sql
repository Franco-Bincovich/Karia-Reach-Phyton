-- 007: Tabla usuarios_reach — usuarios de la aplicacion KarIA Reach.
-- Sin dependencias FK. Password almacenado como hash bcrypt.
CREATE TABLE IF NOT EXISTS usuarios_reach (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  rol TEXT DEFAULT 'user' CHECK (rol IN ('admin', 'user')),
  activo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios_reach(email);
