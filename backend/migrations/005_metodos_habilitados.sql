-- Migración: agrega columna metodos_habilitados a usuarios_reach
-- Ejecutar como superusuario PostgreSQL (ALTER TABLE requiere privilegios sobre la tabla)
ALTER TABLE usuarios_reach
    ADD COLUMN IF NOT EXISTS metodos_habilitados TEXT[]
    DEFAULT ARRAY['claude_ai','apollo','perplexity','apify','scraping_web','carga_manual'];
