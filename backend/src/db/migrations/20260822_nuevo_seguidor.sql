BEGIN;

ALTER TABLE notificacion
    ADD COLUMN usuario_origen_id INT;

ALTER TABLE notificacion
    ADD CONSTRAINT notificacion_usuario_origen_id_fkey
    FOREIGN KEY (usuario_origen_id) REFERENCES usuario(id);

ALTER TABLE notificacion
    DROP CONSTRAINT notificacion_tipo_check;

ALTER TABLE notificacion
    ADD CONSTRAINT notificacion_tipo_check CHECK (
        tipo IN (
            'POSTULACION_NUEVA',
            'POSTULACION_ESTADO',
            'NUEVO_SEGUIDOR'
        )
    );

COMMIT;
