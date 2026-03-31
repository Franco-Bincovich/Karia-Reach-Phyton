-- Bloques de contactos para organizar envios
CREATE TABLE IF NOT EXISTS bloques (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Relacion N:N entre bloques y contactos
CREATE TABLE IF NOT EXISTS bloque_contactos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    bloque_id UUID NOT NULL REFERENCES bloques(id) ON DELETE CASCADE,
    contacto_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bloque_id, contacto_id)
);
