-- [:space:] cubre espacios, tabs, saltos de línea y otros separadores POSIX.
-- Los límites máximos siguen reforzados por VARCHAR o por estas constraints.

ALTER TABLE usuario
    ADD CONSTRAINT usuario_nombre_no_blank_check
    CHECK (nombre ~ '[^[:space:]]');
ALTER TABLE usuario
    ADD CONSTRAINT usuario_headline_no_blank_check
    CHECK (headline ~ '[^[:space:]]');
ALTER TABLE usuario
    ADD CONSTRAINT usuario_ciudad_no_blank_check
    CHECK (ciudad ~ '[^[:space:]]');

ALTER TABLE empresa
    ADD CONSTRAINT empresa_nombre_no_blank_check
    CHECK (nombre ~ '[^[:space:]]');

ALTER TABLE experiencia
    ADD CONSTRAINT experiencia_puesto_no_blank_check
    CHECK (puesto ~ '[^[:space:]]');

-- tables.sql used to leave this CHECK unnamed, so PostgreSQL may have
-- generated publicacion_texto_check in databases created from that file.
ALTER TABLE publicacion DROP CONSTRAINT IF EXISTS publicacion_texto_check;
ALTER TABLE publicacion DROP CONSTRAINT IF EXISTS check_longitud_texto;
ALTER TABLE publicacion
    ADD CONSTRAINT check_longitud_texto
    CHECK (
        LENGTH(texto) BETWEEN 1 AND 3000
        AND texto ~ '[^[:space:]]'
    );

ALTER TABLE oferta
    ADD CONSTRAINT oferta_titulo_no_blank_check
    CHECK (titulo ~ '[^[:space:]]');
ALTER TABLE oferta
    ADD CONSTRAINT oferta_descripcion_no_blank_check
    CHECK (descripcion ~ '[^[:space:]]');

ALTER TABLE promocion DROP CONSTRAINT IF EXISTS promocion_titulo_check;
ALTER TABLE promocion DROP CONSTRAINT IF EXISTS promocion_descripcion_check;
ALTER TABLE promocion
    ADD CONSTRAINT promocion_titulo_check
    CHECK (
        LENGTH(titulo) BETWEEN 1 AND 160
        AND titulo ~ '[^[:space:]]'
    );
ALTER TABLE promocion
    ADD CONSTRAINT promocion_descripcion_check
    CHECK (
        LENGTH(descripcion) BETWEEN 1 AND 3000
        AND descripcion ~ '[^[:space:]]'
    );

ALTER TABLE comentario DROP CONSTRAINT IF EXISTS comentario_contenido_check;
ALTER TABLE comentario
    ADD CONSTRAINT comentario_contenido_check
    CHECK (
        LENGTH(contenido) BETWEEN 1 AND 1000
        AND contenido ~ '[^[:space:]]'
    );

ALTER TABLE mensaje DROP CONSTRAINT IF EXISTS mensaje_contenido_check;
ALTER TABLE mensaje
    ADD CONSTRAINT mensaje_contenido_check
    CHECK (
        LENGTH(contenido) BETWEEN 1 AND 2000
        AND contenido ~ '[^[:space:]]'
    );
