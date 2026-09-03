CREATE INDEX IF NOT EXISTS idx_usuario_nombre_id
    ON usuario (LOWER(nombre), id);

CREATE INDEX IF NOT EXISTS idx_comentario_raiz_publicacion_fecha
    ON comentario (publicacion_id, fecha DESC, id DESC)
    WHERE comentario_padre_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_oferta_publicada_fecha_id
    ON oferta (fecha_publicacion DESC, id DESC)
    WHERE publicada = TRUE;

CREATE INDEX IF NOT EXISTS idx_oferta_empresa_id
    ON oferta (empresa_id, id DESC);

CREATE INDEX IF NOT EXISTS idx_postulacion_usuario_fecha_id
    ON postulacion (usuario_id, fecha DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_postulacion_oferta_fecha_id
    ON postulacion (oferta_id, fecha DESC, id DESC);
