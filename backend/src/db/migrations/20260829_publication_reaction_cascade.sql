BEGIN;

ALTER TABLE reacciones
    DROP CONSTRAINT reacciones_publicacion_id_fkey,
    ADD CONSTRAINT reacciones_publicacion_id_fkey
        FOREIGN KEY (publicacion_id)
        REFERENCES publicacion(id)
        ON DELETE CASCADE;

COMMIT;
