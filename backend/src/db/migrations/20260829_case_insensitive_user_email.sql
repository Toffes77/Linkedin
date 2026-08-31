BEGIN;

LOCK TABLE usuario IN ACCESS EXCLUSIVE MODE;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM usuario
        GROUP BY LOWER(email)
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Existen emails duplicados al ignorar mayusculas; se requiere reconciliacion manual.';
    END IF;
END
$$;

UPDATE usuario
SET email = LOWER(email)
WHERE email <> LOWER(email);

ALTER TABLE usuario
    DROP CONSTRAINT usuario_email_key;

CREATE UNIQUE INDEX uq_usuario_email_lower
    ON usuario (LOWER(email));

COMMIT;
