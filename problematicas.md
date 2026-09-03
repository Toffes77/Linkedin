# Problemáticas pendientes

Este documento contiene únicamente problemas actuales, verificables y accionables del proyecto Atanes. Fue depurado contra el código vigente el 2 de septiembre de 2026. No conserva bugs ya corregidos, descripciones de arquitectura sana, recomendaciones opcionales ni cobertura faltante sin un defecto funcional asociado.

## MEDIAS

### 4. Fotos personales siguen presentes en el historial Git

**Área:** Privacidad / Git / Operación histórica

**Problema:** Las imágenes nuevas ya están ignoradas y los archivos dejaron de estar trackeados en el índice actual, pero copias de fotos de usuario y empresa permanecen en commits anteriores.

**Evidencia:** `backend/.gitignore` excluye `imagenes/*` salvo `.gitkeep`, mientras que `git log --all --name-only -- backend/imagenes` todavía enumera archivos `usuario_*` y `empresa_*` con formatos de imagen.

**Consecuencia:** Quien tenga acceso al historial completo del repositorio puede recuperar imágenes personales eliminadas del árbol actual.

**Qué habría que modificar:** Definir la política de retención/consentimiento y, si el repositorio fue compartido o se publicará, reescribir el historial de forma coordinada y rotar clones remotos.

---

### 7. Aceptar y rechazar simultáneamente una conexión no está serializado

**Área:** Conexiones / Concurrencia

**Problema:** Las respuestas a una invitación leen el estado `pendiente` sin bloqueo. Dos requests pueden validar el mismo estado anterior y aplicar decisiones distintas; dos aceptaciones también pueden crear notificaciones duplicadas.

**Evidencia:** `ConexionService.update()` usa `ConexionRepository.get_by_id()` y luego actualiza/notifica; el Repository no ofrece una lectura `FOR UPDATE` para este flujo.

**Consecuencia:** Puede quedar una conexión rechazada acompañada por una notificación de aceptación, o varias notificaciones para una única aceptación lógica.

**Qué habría que modificar:** Obtener la conexión con row lock, releer y validar su estado dentro de la misma transacción que actualiza y notifica.

---

### 8. Marcar mensajes como leídos puede ocultar un mensaje confirmado después

**Área:** Mensajes / No leídos / Concurrencia

**Problema:** Los no leídos se calculan con `Mensaje.fecha > ultima_lectura`. Un mensaje puede recibir su timestamp, quedar sin confirmar, y confirmarse después de que otra sesión avanzó `ultima_lectura` a `datetime.now()`.

**Evidencia:** `MensajeRepository.create_message()` asigna `datetime.now()` antes del commit; `mark_as_read()` guarda otro `datetime.now()`; `list_contact_summaries()` y `count_unread()` comparan ambos timestamps.

**Consecuencia:** Un mensaje realmente nuevo puede no incrementar nunca el contador ni el punto verde del destinatario.

**Qué habría que modificar:** Registrar el último ID de mensaje efectivamente observado —o un límite transaccional equivalente— en vez de representar la lectura solo con la hora del proceso.

---

### 11. HU11 puede sugerir una relación rechazada que no se puede volver a solicitar

**Área:** Conexiones / Sugerencias de segundo grado

**Problema:** La consulta de sugerencias excluye relaciones aceptadas y pendientes, pero no rechazadas. A la vez, el alta rechaza cualquier relación existente, incluido estado `rechazada`.

**Evidencia:** `ConexionRepository.get_second_degree_suggestions()` construye `relaciones_directas` con estados `aceptada` y `pendiente`; `ConexionService.create()` devuelve conflicto si `get_by_usuarios()` encuentra cualquier fila.

**Consecuencia:** Mi Red puede mostrar una persona con acción “Conectar” que siempre termina en error.

**Qué habría que modificar:** Definir una política única para rechazo: excluir esas relaciones de sugerencias o permitir un reintento controlado reutilizando la fila canónica.

---

### 16. El polling de mensajes puede solaparse y altera la posición de lectura

**Área:** Mensajes / UX / Concurrencia frontend

**Problema:** Cada intervalo dispara refrescos sin guard de request en curso ni cancelación. Además, cualquier cambio en `messages.length` desplaza el historial al fondo aunque el usuario esté leyendo mensajes anteriores.

**Evidencia:** `messages-dock.tsx` usa `setInterval()` para llamar incondicionalmente a `refreshContacts()` y `refreshActiveMessages()`; `chat-window.tsx` ejecuta `scrollTo(scrollHeight)` al cambiar la longitud.

**Consecuencia:** Respuestas lentas pueden sobrescribir estado más nuevo y la llegada de mensajes expulsa al usuario de la posición que estaba leyendo.

**Qué habría que modificar:** Serializar/cancelar ciclos de polling y hacer autoscroll solo cuando el usuario estaba cerca del final.

---

### 17. La búsqueda muestra “Conectar” para uno mismo y relaciones existentes

**Área:** Búsqueda / Conexiones / UX funcional

**Problema:** Todos los resultados usan una `PersonCard` inicializada en estado `idle`; no se excluye al usuario autenticado ni se carga el estado actual de conexión.

**Evidencia:** `frontend/app/buscar/page.tsx` renderiza todos los resultados sin filtro y `frontend/components/network/person-card.tsx` solo conoce estado local `idle/busy/sent`.

**Consecuencia:** Se muestran acciones imposibles para uno mismo, contactos, pendientes o relaciones rechazadas y el usuario solo descubre el problema al recibir el error del backend.

**Qué habría que modificar:** Excluir al usuario actual e incluir/cargar en batch el estado de conexión para representar la acción válida.

---

### 18. El esquema no tiene un historial de migraciones verificable y los metadatos divergen

**Área:** PostgreSQL / Migraciones / SQLAlchemy

**Problema:** Hay scripts SQL manuales sin ledger de versión ni entorno Alembic activo. Las primeras migraciones no son repetibles y `Base.metadata` no describe exactamente algunos índices presentes en `tables.sql`/DB.

**Evidencia:** `backend/src/db/migrations/20260822_*.sql` usa `ADD COLUMN`/`DROP CONSTRAINT` sin precondiciones; Alembic solo figura como dependencia; `comentario_model.py` omite el desempate `id` de los índices y `notificacion_model.py` no declara índices existentes en `tables.sql`.

**Consecuencia:** Una base nueva, parcial o creada desde metadata puede terminar con un esquema diferente; repetir o alterar el orden de scripts falla sin una forma fiable de conocer la versión aplicada.

**Qué habría que modificar:** Establecer una fuente canónica versionada, registrar revisiones aplicadas y alinear Models, bootstrap y migraciones.

## BAJAS

### 19. El Composer presenta acciones que no hacen nada

**Área:** Feed / UX funcional

**Problema:** “Video”, “Foto” y “Escribir artículo” se presentan visualmente como acciones, pero son elementos `<span>` sin interacción.

**Evidencia:** `frontend/components/feed/composer.tsx` renderiza las tres opciones dentro de `.composer-actions` sin botones, enlaces ni handlers.

**Consecuencia:** La interfaz ofrece capacidades aparentes que no responden a ninguna acción.

**Qué habría que modificar:** Ocultarlas hasta implementarlas o conectarlas a un flujo funcional y accesible.
