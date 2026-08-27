DO $$
BEGIN
    CREATE TYPE estado_solicitud_contratacion_promocion AS ENUM (
        'PENDIENTE',
        'ACEPTADA',
        'RECHAZADA'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS promocion (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    titulo VARCHAR(160) NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT promocion_titulo_check
        CHECK (LENGTH(TRIM(titulo)) BETWEEN 1 AND 160),
    CONSTRAINT promocion_descripcion_check
        CHECK (LENGTH(TRIM(descripcion)) BETWEEN 1 AND 3000)
);

CREATE INDEX IF NOT EXISTS idx_promocion_usuario_fecha
    ON promocion (usuario_id, fecha_creacion DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_promocion_fecha
    ON promocion (fecha_creacion DESC, id DESC);

CREATE TABLE IF NOT EXISTS solicitud_contratacion_promocion (
    id SERIAL PRIMARY KEY,
    promocion_id INT NOT NULL REFERENCES promocion(id) ON DELETE CASCADE,
    empresa_id INT NOT NULL REFERENCES empresa(id),
    solicitante_id INT NOT NULL REFERENCES usuario(id),
    estado estado_solicitud_contratacion_promocion NOT NULL DEFAULT 'PENDIENTE',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_solicitud_promocion_empresa_pendiente
    ON solicitud_contratacion_promocion (promocion_id, empresa_id)
    WHERE estado = 'PENDIENTE';
CREATE INDEX IF NOT EXISTS idx_solicitud_promocion_estado
    ON solicitud_contratacion_promocion (
        promocion_id,
        estado,
        fecha_creacion DESC
    );

ALTER TABLE notificacion
    ADD COLUMN IF NOT EXISTS promocion_id INT
        REFERENCES promocion(id) ON DELETE SET NULL;
ALTER TABLE notificacion
    ADD COLUMN IF NOT EXISTS solicitud_contratacion_promocion_id INT
        REFERENCES solicitud_contratacion_promocion(id) ON DELETE SET NULL;

ALTER TABLE notificacion DROP CONSTRAINT IF EXISTS notificacion_tipo_check;
ALTER TABLE notificacion
    ADD CONSTRAINT notificacion_tipo_check CHECK (
        tipo IN (
            'POSTULACION_NUEVA',
            'POSTULACION_ESTADO',
            'NUEVO_SEGUIDOR',
            'NUEVA_INVITACION_CONEXION',
            'CONEXION_ACEPTADA',
            'CONTRATACION_PROMOCION'
        )
    );

CREATE INDEX IF NOT EXISTS idx_notificacion_promocion
    ON notificacion (promocion_id);
