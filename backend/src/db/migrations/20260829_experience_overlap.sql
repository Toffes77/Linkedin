BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;

LOCK TABLE experiencia IN SHARE ROW EXCLUSIVE MODE;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM experiencia AS a
        JOIN experiencia AS b
          ON a.id < b.id
         AND a.usuario_id = b.usuario_id
         AND a.empresa_id = b.empresa_id
         AND daterange(a.desde, a.hasta, '[]')
             && daterange(b.desde, b.hasta, '[]')
    ) THEN
        RAISE EXCEPTION
            'Existen experiencias solapadas para el mismo usuario y empresa; se requiere reconciliacion manual.';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'experiencia'::regclass
          AND conname = 'exclude_experiencia_usuario_empresa_periodo'
    ) THEN
        ALTER TABLE experiencia
            ADD CONSTRAINT exclude_experiencia_usuario_empresa_periodo
            EXCLUDE USING gist (
                usuario_id WITH =,
                empresa_id WITH =,
                daterange(desde, hasta, '[]') WITH &&
            );
    END IF;
END
$$;

COMMIT;
