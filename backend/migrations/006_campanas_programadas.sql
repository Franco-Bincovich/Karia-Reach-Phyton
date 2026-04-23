-- Tabla de campanas programadas (unicas y recurrentes) con soporte para scheduler.
-- Inferida desde repositories/campanas_programadas_repository.py
-- Idempotente — se puede re-ejecutar sin errores.

CREATE TABLE IF NOT EXISTS campanas_programadas (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacion y propiedad
    nombre            TEXT        NOT NULL,
    usuario_id        UUID        NOT NULL REFERENCES usuarios_reach(id) ON DELETE CASCADE,

    -- Recursos referenciados
    template_id       UUID        REFERENCES templates(id) ON DELETE SET NULL,
    bloque_id         UUID        REFERENCES bloques(id)   ON DELETE SET NULL,

    -- Destinatarios (array de UUIDs serializado como JSON)
    contact_ids       JSONB       NOT NULL DEFAULT '[]',

    -- Scheduling
    tipo              TEXT        NOT NULL CHECK (tipo IN ('unica', 'recurrente')),
    fecha_envio       TIMESTAMPTZ,                         -- Solo para tipo='unica'
    dias_semana       JSONB,                               -- Solo para tipo='recurrente': [0..6]
    hora_envio        TIME        NOT NULL,

    -- Estado del ciclo de vida
    estado            TEXT        NOT NULL DEFAULT 'programada'
                                  CHECK (estado IN ('programada', 'ejecutada', 'fallida', 'cancelada')),
    ultima_ejecucion  TIMESTAMPTZ,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campanas_prog_usuario_id ON campanas_programadas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_campanas_prog_estado     ON campanas_programadas(estado);
