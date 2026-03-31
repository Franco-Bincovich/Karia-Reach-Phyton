-- Campanas programadas: unica o recurrente, por usuario
CREATE TABLE IF NOT EXISTS campanas_programadas (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id    UUID        NOT NULL,
    nombre        TEXT        NOT NULL,
    template_id   UUID        NOT NULL REFERENCES templates(id),
    contact_ids   JSONB       NOT NULL DEFAULT '[]',
    bloque_id     UUID,
    tipo          TEXT        NOT NULL CHECK (tipo IN ('unica', 'recurrente')),
    fecha_envio   TIMESTAMPTZ,
    dias_semana   JSONB,
    hora_envio    TEXT        NOT NULL,
    estado        TEXT        NOT NULL DEFAULT 'programada'
                              CHECK (estado IN ('programada', 'ejecutada', 'cancelada', 'fallida')),
    ultima_ejecucion TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campanas_prog_usuario ON campanas_programadas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_campanas_prog_estado  ON campanas_programadas(estado);
