-- Estado explícito de lectura para mensajes privados 1 a 1.
--
-- Los mensajes históricos se inicializan como no leídos de forma conservadora:
-- ultima_lectura no permite demostrar que una fila confirmada tarde haya sido
-- visible. La próxima apertura de cada conversación marcará únicamente las filas
-- que sí sean visibles en esa transacción.
ALTER TABLE mensaje
    ADD COLUMN IF NOT EXISTS leido_por_destinatario BOOLEAN;

ALTER TABLE mensaje
    ALTER COLUMN leido_por_destinatario SET DEFAULT FALSE;

UPDATE mensaje
SET leido_por_destinatario = FALSE
WHERE leido_por_destinatario IS NULL;

ALTER TABLE mensaje
    ALTER COLUMN leido_por_destinatario SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mensaje_conversacion_no_leido
    ON mensaje (conversacion_id, autor_id)
    WHERE leido_por_destinatario = FALSE;
