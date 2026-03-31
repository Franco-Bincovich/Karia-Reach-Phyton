-- Agregar perplexity como origen valido de contactos
ALTER TABLE contacts DROP CONSTRAINT IF EXISTS contacts_origen_check;
ALTER TABLE contacts ADD CONSTRAINT contacts_origen_check
CHECK (origen IN ('ai', 'manual', 'apollo', 'perplexity'));
