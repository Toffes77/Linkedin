BEGIN;

LOCK TABLE conexiones IN ACCESS EXCLUSIVE MODE;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM conexiones
        GROUP BY
            LEAST(usuario_a, usuario_b),
            GREATEST(usuario_a, usuario_b)
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Existen pares de conexiones duplicados o invertidos; se requiere reconciliacion manual.';
    END IF;
END
$$;

ALTER TABLE conexiones
    ADD COLUMN solicitante_id INT;

UPDATE conexiones
SET solicitante_id = usuario_a;

UPDATE conexiones
SET
    usuario_a = LEAST(usuario_a, usuario_b),
    usuario_b = GREATEST(usuario_a, usuario_b);

ALTER TABLE conexiones
    ALTER COLUMN solicitante_id SET NOT NULL,
    ADD CONSTRAINT conexiones_solicitante_id_fkey
        FOREIGN KEY (solicitante_id) REFERENCES usuario(id),
    DROP CONSTRAINT conexiones_check,
    ADD CONSTRAINT ck_conexiones_orden_canonico
        CHECK (usuario_a < usuario_b),
    ADD CONSTRAINT ck_conexiones_solicitante_en_par
        CHECK (solicitante_id IN (usuario_a, usuario_b));

COMMIT;
