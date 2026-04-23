-- Migration tracker — correr UNA SOLA VEZ antes de todas las demas migraciones.
-- Crea la tabla de control y registra las migraciones ya aplicadas.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    aplicada_at TIMESTAMPTZ DEFAULT NOW()
);

-- Registrar migraciones ya aplicadas (ON CONFLICT DO NOTHING es idempotente)
INSERT INTO schema_migrations (version) VALUES
    ('001_initial_schema'),
    ('002_gmail_integrations'),
    ('003_contact_source_scraping'),
    ('004_campanas_constraints'),
    ('005_metodos_habilitados'),
    ('006_campanas_programadas')
ON CONFLICT DO NOTHING;
