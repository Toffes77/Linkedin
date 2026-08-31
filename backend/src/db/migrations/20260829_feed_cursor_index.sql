CREATE INDEX IF NOT EXISTS idx_publicacion_autor_fecha_id
    ON publicacion (autor_id, fecha DESC, id DESC);
