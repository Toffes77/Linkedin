ALTER TABLE mensaje
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'TEXTO';

ALTER TABLE mensaje
    ADD COLUMN IF NOT EXISTS publicacion_id INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'mensaje_tipo_check'
          AND conrelid = 'mensaje'::regclass
    ) THEN
        ALTER TABLE mensaje
            ADD CONSTRAINT mensaje_tipo_check
            CHECK (tipo IN ('TEXTO', 'PUBLICACION'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'mensaje_publicacion_tipo_check'
          AND conrelid = 'mensaje'::regclass
    ) THEN
        ALTER TABLE mensaje
            ADD CONSTRAINT mensaje_publicacion_tipo_check
            CHECK (tipo = 'PUBLICACION' OR publicacion_id IS NULL);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_mensaje_publicacion'
          AND conrelid = 'mensaje'::regclass
    ) THEN
        ALTER TABLE mensaje
            ADD CONSTRAINT fk_mensaje_publicacion
            FOREIGN KEY (publicacion_id)
            REFERENCES publicacion(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_mensaje_publicacion
    ON mensaje (publicacion_id);
