CREATE TABLE IF NOT EXISTS comentario (
    id SERIAL PRIMARY KEY,
    publicacion_id INT NOT NULL,
    usuario_id INT NOT NULL,
    contenido VARCHAR(1000) NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    comentario_padre_id INT,

    CONSTRAINT fk_comentario_publicacion
        FOREIGN KEY (publicacion_id)
        REFERENCES publicacion(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comentario_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuario(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comentario_padre
        FOREIGN KEY (comentario_padre_id)
        REFERENCES comentario(id)
        ON DELETE CASCADE,
    CONSTRAINT comentario_contenido_check
        CHECK (length(trim(contenido)) BETWEEN 1 AND 1000)
);

CREATE INDEX IF NOT EXISTS idx_comentario_publicacion_fecha
    ON comentario (publicacion_id, fecha DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_comentario_padre_fecha
    ON comentario (comentario_padre_id, fecha, id);
