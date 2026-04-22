-- Migración: corrige constraints de tipo y estado en campanas_programadas
ALTER TABLE campanas_programadas DROP CONSTRAINT IF EXISTS campanas_programadas_tipo_check;
ALTER TABLE campanas_programadas ADD CONSTRAINT campanas_programadas_tipo_check
    CHECK (tipo = ANY (ARRAY['una_vez', 'unica', 'recurrente']));

ALTER TABLE campanas_programadas DROP CONSTRAINT IF EXISTS campanas_programadas_estado_check;
ALTER TABLE campanas_programadas ADD CONSTRAINT campanas_programadas_estado_check
    CHECK (estado = ANY (ARRAY['programada','pausada','cancelada','completada','ejecutando','ejecutada','fallida']));
