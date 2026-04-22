-- Schema inicial de KarIA Reach
-- Ejecutar como superusuario PostgreSQL: psql -U postgres -d karia_reach -f 001_initial_schema.sql

-- ─── ENUMS ───────────────────────────────────────────────────────────────────

CREATE TYPE IF NOT EXISTS contact_source AS ENUM (
    'ai',
    'apollo',
    'perplexity',
    'apify',
    'manual',
    'scraping'
);

CREATE TYPE IF NOT EXISTS campaign_status AS ENUM (
    'draft',
    'sending',
    'sent',
    'failed',
    'scheduled'
);

-- ─── TABLAS ──────────────────────────────────────────────────────────────────

-- Usuarios de la plataforma con roles y métodos de búsqueda habilitados
CREATE TABLE IF NOT EXISTS usuarios_reach (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre               TEXT,
    email                TEXT NOT NULL UNIQUE,
    password_hash        TEXT NOT NULL,
    rol                  TEXT NOT NULL DEFAULT 'user' CHECK (rol IN ('user', 'superadmin')),
    activo               BOOLEAN NOT NULL DEFAULT true,
    metodos_habilitados  TEXT[] DEFAULT ARRAY['claude_ai','apollo','perplexity','apify','scraping_web','carga_manual'],
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ
);

-- Contactos B2B con datos de enriquecimiento multi-fuente
CREATE TABLE IF NOT EXISTS contacts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre               TEXT,
    empresa              TEXT,
    cargo                TEXT,
    rubro                TEXT,
    email_empresarial    TEXT,
    email_personal       TEXT,
    telefono_empresa     TEXT,
    telefono_personal    TEXT,
    linkedin_url         TEXT,
    instagram_username   TEXT,
    facebook_url         TEXT,
    twitter_url          TEXT,
    tiktok_username      TEXT,
    whatsapp             TEXT,
    website              TEXT,
    direccion            TEXT,
    ciudad               TEXT,
    pais                 TEXT,
    confianza            SMALLINT CHECK (confianza BETWEEN 0 AND 100),
    origen               contact_source NOT NULL DEFAULT 'manual',
    enrichment_sources   JSONB DEFAULT '[]',
    last_enriched_at     TIMESTAMPTZ,
    usuario_id           UUID REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_contacts_usuario_id      ON contacts(usuario_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email_emp       ON contacts(email_empresarial);
CREATE INDEX IF NOT EXISTS idx_contacts_email_per       ON contacts(email_personal);
CREATE INDEX IF NOT EXISTS idx_contacts_created_at      ON contacts(created_at DESC);

-- Log de enriquecimientos aplicados por contacto y fuente
CREATE TABLE IF NOT EXISTS contact_enrichments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id   UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    usuario_id   UUID REFERENCES usuarios_reach(id) ON DELETE SET NULL,
    source       TEXT NOT NULL,
    fields_added JSONB DEFAULT '[]',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Templates de email con tono y objetivo personalizables
CREATE TABLE IF NOT EXISTS templates (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre     TEXT NOT NULL,
    asunto     TEXT NOT NULL,
    cuerpo     TEXT NOT NULL,
    tono       TEXT,
    objetivo   TEXT,
    usuario_id UUID REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_templates_usuario_id ON templates(usuario_id);

-- Campañas de email con métricas de envío y estado
CREATE TABLE IF NOT EXISTS campaigns (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         TEXT NOT NULL,
    template_id    UUID REFERENCES templates(id) ON DELETE SET NULL,
    contacts_count INTEGER NOT NULL DEFAULT 0,
    sent_count     INTEGER NOT NULL DEFAULT 0,
    failed_count   INTEGER NOT NULL DEFAULT 0,
    status         campaign_status NOT NULL DEFAULT 'draft',
    scheduled_at   TIMESTAMPTZ,
    sent_at        TIMESTAMPTZ,
    usuario_id     UUID REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_usuario_id  ON campaigns(usuario_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_at  ON campaigns(created_at DESC);

-- Resultado individual de envío por contacto dentro de una campaña
CREATE TABLE IF NOT EXISTS campaign_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id          UUID REFERENCES contacts(id) ON DELETE SET NULL,
    email_destinatario  TEXT NOT NULL,
    asunto              TEXT,
    exitoso             BOOLEAN NOT NULL DEFAULT false,
    message_id          TEXT,
    error               TEXT,
    enviado_at          TIMESTAMPTZ,
    opened_at           TIMESTAMPTZ,
    respondido          BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_campaign_results_campaign_id ON campaign_results(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_results_contact_id  ON campaign_results(contact_id);

-- Respuestas recibidas a emails de campañas via Gmail sync
CREATE TABLE IF NOT EXISTS email_replies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    contact_id  UUID REFERENCES contacts(id) ON DELETE SET NULL,
    message_id  TEXT UNIQUE,
    in_reply_to TEXT,
    de          TEXT NOT NULL,
    asunto      TEXT,
    cuerpo      TEXT,
    fecha       TIMESTAMPTZ,
    leido       BOOLEAN NOT NULL DEFAULT false,
    respondido  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_replies_campaign_id ON email_replies(campaign_id);

-- API keys cifradas de integraciones externas por usuario y servicio
CREATE TABLE IF NOT EXISTS integraciones (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    servicio   TEXT NOT NULL,
    api_key    TEXT NOT NULL,
    activo     BOOLEAN NOT NULL DEFAULT true,
    usuario_id UUID REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE (servicio, usuario_id)
);

CREATE INDEX IF NOT EXISTS idx_integraciones_usuario_id ON integraciones(usuario_id);

-- Tokens OAuth Gmail cifrados por usuario para envío autenticado
CREATE TABLE IF NOT EXISTS integraciones_gmail (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id             UUID NOT NULL UNIQUE REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    email                  TEXT NOT NULL,
    refresh_token_cifrado  TEXT NOT NULL,
    access_token_cifrado   TEXT,
    access_token_expira    TIMESTAMPTZ,
    scopes                 TEXT,
    conectado_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo                 BOOLEAN NOT NULL DEFAULT true,
    ultimo_uso             TIMESTAMPTZ,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Listas de contactos reutilizables para asignar a campañas
CREATE TABLE IF NOT EXISTS bloques (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre     TEXT NOT NULL,
    usuario_id UUID REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bloques_usuario_id ON bloques(usuario_id);

-- Relación many-to-many entre bloques y contactos
CREATE TABLE IF NOT EXISTS bloques_contactos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bloque_id   UUID NOT NULL REFERENCES bloques(id) ON DELETE CASCADE,
    contacto_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (bloque_id, contacto_id)
);

CREATE INDEX IF NOT EXISTS idx_bloques_contactos_bloque_id ON bloques_contactos(bloque_id);

-- Campañas con envío diferido: una vez en fecha/hora o recurrente por días de semana
CREATE TABLE IF NOT EXISTS campanas_programadas (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre           TEXT NOT NULL,
    usuario_id       UUID NOT NULL REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    template_id      UUID REFERENCES templates(id) ON DELETE SET NULL,
    bloque_id        UUID REFERENCES bloques(id) ON DELETE SET NULL,
    tipo             TEXT NOT NULL CHECK (tipo IN ('una_vez', 'unica', 'recurrente')),
    estado           TEXT NOT NULL DEFAULT 'programada'
                         CHECK (estado IN ('programada','pausada','cancelada','completada','ejecutando','ejecutada','fallida')),
    contact_ids      JSONB DEFAULT '[]',
    dias_semana      JSONB DEFAULT '[]',
    hora_envio       TIME,
    fecha_envio      TIMESTAMPTZ,
    ultima_ejecucion TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campanas_prog_usuario_id ON campanas_programadas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_campanas_prog_estado     ON campanas_programadas(estado);
