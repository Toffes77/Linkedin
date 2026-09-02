-- Los timestamps naive históricos fueron generados por procesos y por una
-- sesión PostgreSQL configurados en America/Buenos_Aires. La zona se expresa
-- en cada USING para que la conversión no dependa de la sesión que migra.

ALTER TABLE usuario ALTER COLUMN fecha_registro DROP DEFAULT;
ALTER TABLE usuario ALTER COLUMN fecha_registro TYPE TIMESTAMPTZ
    USING fecha_registro AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE usuario ALTER COLUMN fecha_registro SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE promocion ALTER COLUMN fecha_creacion DROP DEFAULT;
ALTER TABLE promocion ALTER COLUMN fecha_creacion TYPE TIMESTAMPTZ
    USING fecha_creacion AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE promocion ALTER COLUMN fecha_creacion SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE solicitud_contratacion_promocion
    ALTER COLUMN fecha_creacion DROP DEFAULT;
ALTER TABLE solicitud_contratacion_promocion
    ALTER COLUMN fecha_creacion TYPE TIMESTAMPTZ
    USING fecha_creacion AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE solicitud_contratacion_promocion
    ALTER COLUMN fecha_creacion SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE solicitud_contratacion_promocion
    ALTER COLUMN fecha_respuesta TYPE TIMESTAMPTZ
    USING fecha_respuesta AT TIME ZONE 'America/Buenos_Aires';

ALTER TABLE publicacion ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE publicacion ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE publicacion ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE comentario ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE comentario ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE comentario ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE oferta ALTER COLUMN fecha_publicacion TYPE TIMESTAMPTZ
    USING fecha_publicacion AT TIME ZONE 'America/Buenos_Aires';

ALTER TABLE postulacion ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE postulacion ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE postulacion ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE conexiones ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE conexiones ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE conexiones ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE notificacion ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE notificacion ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE notificacion ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE seguimiento ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE seguimiento ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE seguimiento ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE conversacion ALTER COLUMN fecha_creacion DROP DEFAULT;
ALTER TABLE conversacion ALTER COLUMN fecha_creacion TYPE TIMESTAMPTZ
    USING fecha_creacion AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE conversacion ALTER COLUMN fecha_creacion SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE conversacion ALTER COLUMN fecha_ultimo_mensaje TYPE TIMESTAMPTZ
    USING fecha_ultimo_mensaje AT TIME ZONE 'America/Buenos_Aires';

ALTER TABLE conversacion_usuario ALTER COLUMN ultima_lectura DROP DEFAULT;
ALTER TABLE conversacion_usuario ALTER COLUMN ultima_lectura TYPE TIMESTAMPTZ
    USING ultima_lectura AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE conversacion_usuario ALTER COLUMN ultima_lectura
    SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE mensaje ALTER COLUMN fecha DROP DEFAULT;
ALTER TABLE mensaje ALTER COLUMN fecha TYPE TIMESTAMPTZ
    USING fecha AT TIME ZONE 'America/Buenos_Aires';
ALTER TABLE mensaje ALTER COLUMN fecha SET DEFAULT CURRENT_TIMESTAMP;
