BEGIN;

ALTER TABLE notificacion
    DROP CONSTRAINT notificacion_tipo_check;

ALTER TABLE notificacion
    ADD CONSTRAINT notificacion_tipo_check CHECK (
        tipo IN (
            'POSTULACION_NUEVA',
            'POSTULACION_ESTADO',
            'NUEVO_SEGUIDOR',
            'NUEVA_INVITACION_CONEXION',
            'CONEXION_ACEPTADA'
        )
    );

COMMIT;
