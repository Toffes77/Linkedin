BEGIN;

ALTER TABLE publicacion DROP CONSTRAINT IF EXISTS publicacion_texto_check;
ALTER TABLE publicacion DROP CONSTRAINT IF EXISTS check_longitud_texto;
ALTER TABLE publicacion
    ADD CONSTRAINT check_longitud_texto
    CHECK (
        LENGTH(texto) <= 3000
        AND (LENGTH(texto) = 0 OR texto ~ '[^[:space:]]')
    );

CREATE TABLE publicacion_multimedia (
    id SERIAL PRIMARY KEY,
    publicacion_id INT NOT NULL,
    ruta VARCHAR(255) NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    orden INT NOT NULL,

    FOREIGN KEY (publicacion_id) REFERENCES publicacion(id) ON DELETE CASCADE,
    CONSTRAINT publicacion_multimedia_tipo_check
        CHECK (tipo IN ('IMAGEN', 'VIDEO')),
    CONSTRAINT publicacion_multimedia_orden_check CHECK (orden >= 0),
    CONSTRAINT uq_publicacion_multimedia_orden UNIQUE (publicacion_id, orden)
);

CREATE INDEX idx_publicacion_multimedia_publicacion
    ON publicacion_multimedia (publicacion_id, orden);

COMMIT;
