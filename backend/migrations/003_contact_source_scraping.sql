-- Migración: agrega valor 'scraping' al enum contact_source
-- Ejecutar como superusuario PostgreSQL (ALTER TYPE requiere privilegios elevados)
ALTER TYPE contact_source ADD VALUE IF NOT EXISTS 'scraping';
