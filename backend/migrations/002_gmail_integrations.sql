-- Migración 002: tabla de integraciones Gmail OAuth por usuario
-- Ejecutar manualmente en pgAdmin contra la DB karia_reach.

CREATE TABLE IF NOT EXISTS integraciones_gmail (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id            UUID        NOT NULL UNIQUE REFERENCES usuarios_reach(id) ON DELETE CASCADE,
    email                 TEXT        NOT NULL,
    refresh_token_cifrado TEXT        NOT NULL,
    access_token_cifrado  TEXT,
    access_token_expira   TIMESTAMPTZ,
    scopes                TEXT        NOT NULL,
    conectado_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_uso            TIMESTAMPTZ,
    activo                BOOLEAN     NOT NULL DEFAULT true,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gmail_usuario_activo
    ON integraciones_gmail(usuario_id, activo);

GRANT SELECT, INSERT, UPDATE, DELETE ON integraciones_gmail TO karia_reach_user;
