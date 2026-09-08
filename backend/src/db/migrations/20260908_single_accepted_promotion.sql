-- Incremental and data-preserving: abort instead of changing any inconsistent row.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM solicitud_contratacion_promocion
        WHERE estado = 'ACEPTADA'
        GROUP BY promocion_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'No se puede crear uq_solicitud_promocion_aceptada: hay promociones con más de una solicitud aceptada.';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_solicitud_promocion_aceptada
    ON solicitud_contratacion_promocion (promocion_id)
    WHERE estado = 'ACEPTADA';
