# Problemáticas pendientes

Este documento contiene únicamente problemas actuales, verificables y accionables del proyecto Atanes. Fue depurado contra el código vigente el 29 de agosto de 2026. No conserva bugs ya corregidos, descripciones de arquitectura sana, recomendaciones opcionales ni cobertura faltante sin un defecto funcional asociado.

## MEDIAS

### 4. Fotos personales siguen presentes en el historial Git

**Área:** Privacidad / Git / Operación histórica

**Problema:** Las imágenes nuevas ya están ignoradas y los archivos dejaron de estar trackeados en el índice actual, pero copias de fotos de usuario y empresa permanecen en commits anteriores.

**Evidencia:** `backend/.gitignore` excluye `imagenes/*` salvo `.gitkeep`, mientras que `git log --all --name-only -- backend/imagenes` todavía enumera archivos `usuario_*` y `empresa_*` con formatos de imagen.

**Consecuencia:** Quien tenga acceso al historial completo del repositorio puede recuperar imágenes personales eliminadas del árbol actual.

**Qué habría que modificar:** Definir la política de retención/consentimiento y, si el repositorio fue compartido o se publicará, reescribir el historial de forma coordinada y rotar clones remotos.

---

### 5. Crear una oferta inicialmente publicada usa dos commits

**Área:** Ofertas / Transacciones

**Problema:** Se inserta primero la oferta con `publicada=true` y se confirma; después se asigna `fecha_publicacion` y se ejecuta un segundo commit.

**Evidencia:** `OfertaService.create()` llama a `OfertaRepository.create()` —que hace `commit`— y luego a `OfertaRepository.update()` para guardar la fecha.

**Consecuencia:** Un fallo entre ambos commits deja una oferta visible sin fecha de publicación, rompiendo estadísticas y el invariante del dominio.

**Qué habría que modificar:** Calcular la fecha antes del insert o mantener ambas escrituras dentro de una única transacción y un solo commit.

---

### 6. Algunas colisiones de unicidad concurrentes todavía responden 500

**Área:** Errores HTTP / Concurrencia / Integridad

**Problema:** PostgreSQL impide duplicados en postulaciones, reacciones, seguimientos y membresías, pero esos flujos no convierten el `IntegrityError` esperado en un conflicto de negocio.

**Evidencia:** `PostulacionService.create()`, `SeguimientoService.follow()` y `EmpresaUsuarioService.create()` solo usan captura genérica o ninguna captura específica; `ReaccionesService.create()` deja que el commit del Repository propague `IntegrityError`.

**Consecuencia:** En requests simultáneos la integridad se conserva, pero el request perdedor recibe un 500 y puede dejar mensajes de error incoherentes en frontend.

**Qué habría que modificar:** Hacer rollback y mapear únicamente las constraints conocidas a `409 Conflict`, sin exponer detalles SQL.

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

### 9. Las fechas persistentes no tienen zona horaria

**Área:** Fechas / PostgreSQL / Frontend

**Problema:** El dominio mezcla `TIMESTAMP WITHOUT TIME ZONE`, `datetime.now()` naive e ISO sin offset. JWT usa UTC aware, pero publicaciones, ofertas, mensajes, postulaciones y notificaciones no.

**Evidencia:** Los Models declaran `DateTime` sin `timezone=True`; `tables.sql` usa `TIMESTAMP`; `OfertaService` y `MensajeRepository` generan fechas con `datetime.now()`; `frontend/lib/format.ts` interpreta esas cadenas con `Date`.

**Consecuencia:** Con servidor, PostgreSQL y navegador en zonas diferentes se muestran horarios desplazados y pueden calcularse incorrectamente los días desde publicación.

**Qué habría que modificar:** Normalizar persistencia y cálculos a UTC timezone-aware, migrar datos existentes con una zona de origen definida y convertir solo al presentar.

---

### 10. Varias entidades aceptan texto compuesto solo por espacios

**Área:** Validación API / PostgreSQL

**Problema:** Usuario, empresa, experiencia, publicación y oferta usan `min_length` sin trim uniforme. La constraint de publicación usa `LENGTH(texto)` en lugar de `LENGTH(TRIM(texto))`.

**Evidencia:** Los DTOs/Schemas de esos módulos carecen de validadores de trim equivalentes a promociones, comentarios y mensajes; `publicacion_model.py` y `tables.sql` aceptan espacios como contenido.

**Consecuencia:** Mediante una petición directa se pueden persistir nombres, headlines, puestos, publicaciones, títulos o descripciones visualmente vacíos.

**Qué habría que modificar:** Normalizar y rechazar whitespace-only en backend para create/update y reforzar con checks de PostgreSQL donde el campo sea obligatorio.

---

### 11. HU11 puede sugerir una relación rechazada que no se puede volver a solicitar

**Área:** Conexiones / Sugerencias de segundo grado

**Problema:** La consulta de sugerencias excluye relaciones aceptadas y pendientes, pero no rechazadas. A la vez, el alta rechaza cualquier relación existente, incluido estado `rechazada`.

**Evidencia:** `ConexionRepository.get_second_degree_suggestions()` construye `relaciones_directas` con estados `aceptada` y `pendiente`; `ConexionService.create()` devuelve conflicto si `get_by_usuarios()` encuentra cualquier fila.

**Consecuencia:** Mi Red puede mostrar una persona con acción “Conectar” que siempre termina en error.

**Qué habría que modificar:** Definir una política única para rechazo: excluir esas relaciones de sugerencias o permitir un reintento controlado reutilizando la fila canónica.

---

### 12. Los comentarios cargan y recorren el árbol completo sin límite

**Área:** Comentarios / Rendimiento / Robustez

**Problema:** Abrir comentarios materializa todas las filas de la publicación y reconstruye/recorre recursivamente todo el árbol tanto en backend como en frontend.

**Evidencia:** `ComentarioRepository.get_all_by_publicacion()` termina en `.all()`; `ComentarioMapper.to_response_tree()` usa `build_node()` recursivo; `comments-section.tsx` y `comment-item.tsx` vuelven a recorrer/renderizar recursivamente.

**Consecuencia:** Publicaciones con muchos comentarios o cadenas profundas pueden consumir memoria excesiva o exceder el stack.

**Qué habría que modificar:** Paginar raíces/respuestas y usar reconstrucción iterativa o un límite operativo explícito de profundidad.

---

### 13. Búsquedas y listados centrales no tienen paginación ni orden estable

**Área:** Perfiles / Ofertas / Postulaciones / Promociones

**Problema:** La búsqueda de perfiles, ofertas públicas y por empresa, postulaciones por usuario/oferta y promociones propias devuelven colecciones completas. Varias consultas carecen de `ORDER BY` determinista.

**Evidencia:** `UsuarioRepository.search()`, `OfertaRepository.get_publicadas*()`, `PostulacionRepository.get_by_*()` y `PromocionRepository.get_by_user()` terminan en `.all()` sin contrato paginado; los tres primeros grupos no siempre ordenan.

**Consecuencia:** La latencia y memoria crecen sin límite y el orden visible puede variar entre requests.

**Qué habría que modificar:** Añadir paginación con máximos, orden total estable —incluido desempate por ID— e índices acordes a las consultas reales.

---

### 14. El frontend genera fan-out de requests y conteos por publicación

**Área:** Feed / Perfiles / Empleos / Rendimiento

**Problema:** Cada página del feed solicita autores por separado; cada `PostCard` pide contadores de reacciones y comentarios, y el conteo de reacciones ejecuta cuatro `COUNT`. Perfil y Empleos también piden empresas una por una.

**Evidencia:** `frontend/app/feed/page.tsx` usa `usersApi.get()` por autor; `post-card.tsx` hace dos requests por publicación; `ReaccionRepository.count_by_publicacion_and_tipo()` se invoca una vez por cada tipo; Perfil y Empleos usan `Promise.all(...companiesApi.get(id))`.

**Consecuencia:** Una vista pequeña produce decenas de requests HTTP y consultas auxiliares, degradando carga y aumentando contención de conexiones.

**Qué habría que modificar:** Enriquecer respuestas o agregar endpoints batch y calcular reacciones con un único `GROUP BY tipo`.

---

### 15. Un error transitorio cierra definitivamente el infinite scroll

**Área:** Feed / UX funcional

**Problema:** Si falla una página posterior, el frontend cambia `hasMore` a `false`, elimina el sentinel y no ofrece reintento.

**Evidencia:** El `catch` de `loadNextPage()` en `frontend/app/feed/page.tsx` actualiza tanto `hasMoreRef.current` como el estado `hasMore` a `false`.

**Consecuencia:** Un corte temporal de red hace parecer que el feed terminó y oculta contenido restante hasta recargar toda la página.

**Qué habría que modificar:** Separar “error de carga” de “fin de resultados”, conservar la página pendiente y ofrecer retry.

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
