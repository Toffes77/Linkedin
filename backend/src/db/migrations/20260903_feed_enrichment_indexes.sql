CREATE INDEX IF NOT EXISTS idx_reacciones_publicacion_tipo
    ON reacciones (publicacion_id, tipo);
