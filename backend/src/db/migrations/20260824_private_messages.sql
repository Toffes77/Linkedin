CREATE TABLE IF NOT EXISTS conversacion (
    id SERIAL PRIMARY KEY,
    usuario_menor_id INT NOT NULL REFERENCES usuario(id),
    usuario_mayor_id INT NOT NULL REFERENCES usuario(id),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_ultimo_mensaje TIMESTAMP,
    CONSTRAINT conversacion_par_ordenado_check
        CHECK (usuario_menor_id < usuario_mayor_id),
    CONSTRAINT uq_conversacion_par_privado
        UNIQUE (usuario_menor_id, usuario_mayor_id)
);

CREATE TABLE IF NOT EXISTS conversacion_usuario (
    conversacion_id INT NOT NULL REFERENCES conversacion(id) ON DELETE CASCADE,
    usuario_id INT NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    ultima_lectura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (conversacion_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS mensaje (
    id SERIAL PRIMARY KEY,
    conversacion_id INT NOT NULL REFERENCES conversacion(id) ON DELETE CASCADE,
    autor_id INT NOT NULL,
    contenido VARCHAR(2000) NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensaje_autor_participante
        FOREIGN KEY (conversacion_id, autor_id)
        REFERENCES conversacion_usuario(conversacion_id, usuario_id)
        ON DELETE CASCADE,
    CONSTRAINT mensaje_contenido_check
        CHECK (length(trim(contenido)) BETWEEN 1 AND 2000)
);

CREATE INDEX IF NOT EXISTS idx_conversacion_ultimo_mensaje
    ON conversacion (fecha_ultimo_mensaje);
CREATE INDEX IF NOT EXISTS idx_conversacion_usuario_usuario
    ON conversacion_usuario (usuario_id, conversacion_id);
CREATE INDEX IF NOT EXISTS idx_mensaje_conversacion_fecha
    ON mensaje (conversacion_id, fecha, id);
