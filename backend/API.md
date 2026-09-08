# API Atanes

Referencia legible de la API REST implementada en `backend/src`. La fuente de verdad para rutas, métodos y schemas es el código actual; Swagger genera el contrato interactivo a partir de los mismos routers.

## Acceso y convenciones

- URL local del backend: `http://localhost:8000`.
- Base de los endpoints de negocio: `http://localhost:8000/api`.
- Swagger UI: [`http://localhost:8000/docs`](http://localhost:8000/docs).
- Esquema OpenAPI: [`http://localhost:8000/openapi.json`](http://localhost:8000/openapi.json).
- Health check: [`http://localhost:8000/health`](http://localhost:8000/health).
- Contenido: JSON salvo los endpoints de imágenes y multimedia, que usan `multipart/form-data`.
- Fechas: `YYYY-MM-DD`; las fechas con hora se serializan como fecha/hora ISO 8601.
- Los identificadores son enteros.

### Autenticación

`POST /api/auth/login` devuelve `access_token` y `token_type` y también establece la cookie HttpOnly `access_token`. Para clientes que no usan cookies, enviar:

```http
Authorization: Bearer <jwt-ficticio>
```

El encabezado Bearer tiene prioridad sobre la cookie. Un endpoint marcado como **requerida** usa `get_current_user`; uno marcado como **opcional** puede atender una solicitud anónima y, si recibe un JWT válido, personaliza la respuesta. Los endpoints públicos no necesitan autenticación.

Swagger puede usar la cookie creada por el login desde el mismo origen de `/docs`; también permite autorizar el esquema Bearer.

### Errores

Las excepciones de dominio manejadas por la API tienen este formato:

```json
{
  "error": "NotFoundError",
  "message": "Recurso no encontrado"
}
```

Los códigos de dominio son:

- `400 Bad Request`: regla de negocio o cursor inválido.
- `401 Unauthorized`: falta el token, es inválido o las credenciales no coinciden.
- `403 Forbidden`: el usuario está autenticado, pero no tiene permiso.
- `404 Not Found`: recurso inexistente o no visible para ese usuario.
- `409 Conflict`: duplicado, transición inválida o conflicto con el estado actual.
- `422 Unprocessable Entity`: FastAPI/Pydantic rechazó parámetros, body o formulario; conserva el formato estándar `{"detail": [...]}`.

Un `204 No Content` no devuelve body. Los errores inesperados no forman parte de un contrato estable y pueden resultar en `500`.

### Paginación

Las respuestas de cursor tienen esta forma conceptual:

```text
items: [...]          elementos de la página
next_cursor: string | null
has_more: boolean
```

Cuando `has_more` es `true`, enviar `next_cursor` sin modificarlo y conservar los mismos filtros. Los cursores están ligados al recurso, usuario y filtros de la consulta; un cursor inválido o usado con otro filtro devuelve `400`. Los endpoints de comentarios, ofertas y postulaciones usan cursor; mensajes, notificaciones y publicaciones por autor usan `limit`/`offset`; el tablón de promociones usa `page`/`page_size`.

### Roles de empresa

Los roles actuales son `OWNER`, `RECRUITER` y `COLLABORATOR`.

- `OWNER`: puede editar la empresa, administrar miembros y gestionar ofertas, postulaciones y estadísticas.
- `RECRUITER`: puede gestionar ofertas, postulaciones y estadísticas, pero no editar la empresa ni miembros.
- `COLLABORATOR`: solo representa pertenencia; no habilita acciones administrativas.

La empresa debe conservar al menos un `OWNER`. Una contratación exitosa agrega `COLLABORATOR` solamente si el usuario todavía no pertenece a la empresa.

## Autenticación

### `POST /api/auth/login` — Iniciar sesión

Autenticación: **no requerida**.

Body `LoginSchema`:

- `email` (email): email registrado.
- `password` (string): contraseña actual.

Respuestas:

- `200`: `TokenSchema` con `access_token` y `token_type` (`bearer`), y cookie HttpOnly `access_token`.
- `401`: credenciales inválidas.
- `422`: body inválido.

### `POST /api/auth/logout` — Cerrar sesión

Autenticación: **no requerida**.

Sin body. Elimina la cookie `access_token` si existe.

Respuestas:

- `200`: `{"message": "Sesión cerrada correctamente"}`.

## Usuarios y perfiles

### `POST /api/usuarios` — Registrar usuario

Autenticación: **no requerida**.

Body `CreateUsuarioSchema`: `email`, `password` (mínimo 8 caracteres), `nombre`, `headline` y `ciudad`. La ciudad debe pertenecer al catálogo; los textos se recortan y normalizan.

Respuestas:

- `201`: `GetUsuarioSchema` (`id`, `nombre`, `headline`, `ciudad`, `foto_perfil_url`, `experiencias`). Nunca contiene password ni password hash.
- `400`: ciudad no válida.
- `409`: el email ya está registrado.
- `422`: body inválido.

### `GET /api/usuarios/me` — Obtener mi perfil

Autenticación: **requerida**.

Sin parámetros ni body.

Respuestas:

- `200`: `GetUsuarioSchema`.
- `401`: autenticación ausente o inválida.

### `GET /api/usuarios/{usuario_id}` — Obtener perfil público

Autenticación: **pública**.

Path: `usuario_id` es el usuario a consultar.

Respuestas:

- `200`: `GetUsuarioSchema`.
- `404`: usuario inexistente.
- `422`: `usuario_id` no es entero.

### `PUT /api/usuarios/me` — Actualizar mi perfil

Autenticación: **requerida**.

Body `UpdateUsuarioSchema`; todos son opcionales: `nombre`, `headline`, `ciudad`. Los campos omitidos conservan su valor.

Respuestas:

- `200`: `GetUsuarioSchema` actualizado.
- `400`: ciudad no válida.
- `401`: autenticación ausente o inválida.
- `404`: usuario inexistente durante la actualización.
- `422`: body inválido o con campos extra.

### `PUT /api/usuarios/me/foto-perfil` — Actualizar foto de perfil

Autenticación: **requerida**. Content-Type: `multipart/form-data`.

Formulario: `foto` (archivo) en JPG, JPEG, PNG o WEBP, máximo 5 MiB. Se valida el contenido real de la imagen y no solo su extensión.

Respuestas:

- `200`: `GetUsuarioSchema` con la nueva `foto_perfil_url`.
- `400`: formato, contenido, nombre o tamaño de archivo inválido.
- `401`: autenticación ausente o inválida.
- `422`: formulario incompleto.

### `PUT /api/usuarios/me/password` — Cambiar contraseña

Autenticación: **requerida**.

Body `UpdatePasswordSchema`: `password_actual` y `password_nueva` (mínimo 8 caracteres). La nueva debe ser diferente de la actual.

Respuestas:

- `200`: `PasswordUpdateResponseSchema` con mensaje de confirmación.
- `400`: la nueva contraseña coincide con la actual.
- `401`: contraseña actual incorrecta o autenticación inválida.
- `422`: body inválido.

### `GET /api/usuarios/{usuario_id}/sugerencias` — Sugerencias de segundo grado

Autenticación: **pública**.

Path: `usuario_id` es el usuario para el que se calculan sugerencias.

Respuestas:

- `200`: lista de `GetUsuarioSchema`.
- `404`: usuario inexistente.
- `422`: path inválido.

### `GET /api/buscar/usuarios` — Buscar usuarios

Autenticación: **pública**.

Query:

- `q` (requerido): texto de 1 a 200 caracteres.
- `ciudad` (opcional): filtro de 1 a 100 caracteres.
- `limit` (opcional, default `20`, máximo `50`).
- `cursor` (opcional): cursor opaco de la página anterior.

Respuesta `200`: `CursorPageSchema[GetUsuarioSchema]`. `400` si el cursor no es válido; `422` si falla la validación.

## Experiencias laborales

### `POST /api/usuarios/{usuario_id}/experiencias` — Agregar experiencia

Autenticación: **requerida**; `usuario_id` debe coincidir con el usuario autenticado.

Body `CreateExperienciaSchema`:

- `empresa_id` (int): empresa existente.
- `puesto` (string): 1 a 100 caracteres.
- `desde` (date): fecha de inicio.
- `hasta` (date | null, opcional): fecha de finalización; `null` significa vigente.

Respuestas:

- `201`: `GetExperienciaSchema`.
- `401`: autenticación ausente o inválida.
- `403`: se intenta modificar la experiencia de otro usuario.
- `404`: usuario o empresa inexistente.
- `409`: período solapado con otra experiencia del usuario en la misma empresa.
- `422`: fechas o body inválidos.

### `PUT /api/experiencias/{experiencia_id}` — Editar experiencia

Autenticación: **requerida**; solo el propietario de la experiencia.

Path `experiencia_id`: experiencia propia a modificar.

Body `UpdateExperienciaSchema`: `empresa_id`, `puesto`, `desde` y `hasta`, todos opcionales. Los campos enviados reemplazan el valor existente; `hasta: null` deja la experiencia vigente. La empresa debe existir y el período final no puede ser anterior al inicial ni solaparse con otra experiencia del usuario en la misma empresa.

Respuestas: `200` `GetExperienciaSchema`; `401` autenticación ausente o inválida; `403` la experiencia pertenece a otro usuario; `404` experiencia o empresa inexistente; `409` período solapado; `422` body/path inválidos.

### `DELETE /api/experiencias/{experiencia_id}` — Eliminar experiencia

Autenticación: **requerida**; solo el propietario de la experiencia.

Respuesta `204` sin body; `401` autenticación ausente o inválida; `403` la experiencia pertenece a otro usuario; `404` experiencia inexistente.

## Empresas, miembros y roles

### `GET /api/empresas` — Buscar empresas

Autenticación: **pública**.

Query `q` (requerido): nombre o texto parcial de 1 a 100 caracteres.

Respuestas: `200` lista de `GetEmpresaSchema`; `422` si falla la query.

### `GET /api/empresas/me` — Listar mis empresas

Autenticación: **requerida**.

Respuesta `200`: lista de `GetMiEmpresaSchema`, cada elemento contiene `empresa` y `rol`. `401` si falta autenticación.

### `POST /api/empresas` — Crear empresa

Autenticación: **requerida**.

Body `CreateEmpresaSchema`: `nombre` (1–100), `industria` opcional (máximo 100) y `sitio_web` opcional (`HttpUrl`). El creador recibe `OWNER`.

Respuestas: `201` `GetEmpresaSchema`; `401` autenticación inválida; `422` body inválido.

### `GET /api/empresas/batch` — Obtener empresas por lote

Autenticación: **pública**.

Query `ids`: repetir el parámetro para enviar entre 1 y 50 IDs, por ejemplo `?ids=10&ids=20`. Se eliminan duplicados y se conservan los IDs existentes en el orden solicitado.

Respuestas: `200` lista de `GetEmpresaSchema`; `400` lote vacío o fuera de rango; `422` query inválida.

### `GET /api/empresas/{empresa_id}` — Obtener empresa

Autenticación: **pública**.

Respuesta `200`: `GetEmpresaSchema` (`id`, `nombre`, `industria`, `sitio_web`, `foto_perfil_url`). `404` si no existe; `422` si el path es inválido.

### `PUT /api/empresas/{empresa_id}` — Actualizar empresa

Autenticación: **requerida**, rol **OWNER**.

Body `UpdateEmpresaSchema`: `nombre`, `industria` y `sitio_web`, todos opcionales; los omitidos conservan su valor.

Respuestas: `200` `GetEmpresaSchema`; `401` sin autenticación; `403` sin OWNER; `404` empresa inexistente; `422` body inválido.

### `PUT /api/empresas/{empresa_id}/foto-perfil` — Actualizar logo

Autenticación: **requerida**, rol **OWNER**. Multipart con `foto`: JPG, JPEG, PNG o WEBP, máximo 5 MiB.

Respuestas: `200` `GetEmpresaSchema`; `400` archivo inválido; `401` sin autenticación; `403` sin OWNER; `404` empresa inexistente; `422` formulario inválido.

### `GET /api/empresas/{empresa_id}/usuarios` — Listar miembros administrables

Autenticación: **requerida**, rol **OWNER**.

Respuesta `200`: lista de `GetEmpresaUsuarioSchema` (`empresa_id`, `usuario_id`, `rol`). `401`, `403` o `404` según autenticación, rol o empresa.

### `GET /api/empresas/{empresa_id}/usuarios/candidatos` — Buscar candidatos a miembro

Autenticación: **requerida**, rol **OWNER**.

Query: `q` requerido (mínimo 2, máximo 100), `limit` default `10` máximo `20`, `cursor` opcional. Excluye usuarios que ya pertenecen a la empresa.

Respuesta `200`: `CursorPageSchema[GetUsuarioSchema]`; `400` cursor inválido; `401`/`403`/`404` por autenticación, rol o empresa; `422` query inválida.

### `GET /api/empresas/{empresa_id}/miembros` — Listar miembros públicos

Autenticación: **pública**.

Respuesta `200`: lista de `GetMiembroEmpresaSchema` (`usuario_id`, `nombre`, `headline`, `foto_perfil_url`, `rol`); `404` si la empresa no existe.

### `POST /api/empresas/{empresa_id}/usuarios` — Agregar miembro

Autenticación: **requerida**, rol **OWNER**.

Body `CreateEmpresaUsuarioSchema`: `usuario_id` y `rol` (`OWNER`, `RECRUITER` o `COLLABORATOR`).

Respuestas: `201` `GetEmpresaUsuarioSchema`; `401`/`403`/`404` por autenticación, rol o recurso; `409` si ya pertenece; `422` body inválido.

### `PATCH /api/empresas/{empresa_id}/usuarios/{usuario_id}` — Cambiar rol

Autenticación: **requerida**, rol **OWNER**.

Body `UpdateEmpresaUsuarioSchema`: `rol` (`OWNER`, `RECRUITER` o `COLLABORATOR`). No se puede degradar o eliminar el último OWNER.

Respuestas: `200` `GetEmpresaUsuarioSchema`; `401`/`403`/`404` por autenticación, rol o membresía; `409` si se perdería el último OWNER; `422` body/path inválidos.

### `DELETE /api/empresas/{empresa_id}/usuarios/{usuario_id}` — Eliminar miembro

Autenticación: **requerida**, rol **OWNER**.

Respuestas: `204` sin body; `401`/`403`/`404` por autenticación, rol o membresía; `409` si se intenta eliminar el último OWNER; `422` path inválido.

## Conexiones

### `GET /api/conexiones/resumen` — Resumen de red

Autenticación: **requerida**.

Respuesta `200`: `ResumenRedResponseSchema` con `invitaciones_enviadas`, `contactos` y `siguiendo`. `401` si falta autenticación.

### `GET /api/conexiones/invitaciones-recibidas` — Invitaciones recibidas

Autenticación: **requerida**.

Respuesta `200`: lista de `InvitacionRecibidaResponseSchema`, que incluye el objeto `usuario` del remitente. `401` si falta autenticación.

### `GET /api/conexiones/estado/{usuario_id}` — Estado de conexión

Autenticación: **requerida**.

Path `usuario_id`: otro usuario. Respuesta `200` `EstadoConexionResponseSchema`; `estado` puede ser `SIN_CONEXION`, `PENDIENTE_ENVIADA`, `PENDIENTE_RECIBIDA`, `CONECTADO` o `RECHAZADA`. `404` si el usuario no existe.

### `POST /api/conexiones` — Enviar invitación

Autenticación: **requerida**.

Body `CreateConexionSchema`: `usuario_a` (debe ser el usuario autenticado) y `usuario_b` (destinatario).

Respuestas: `201` `GetConexionSchema` con estado `pendiente`; `401` autenticación inválida; `403` si `usuario_a` no coincide; `404` usuario inexistente; `409` auto-invitación o relación ya existente; `422` body inválido.

### `PATCH /api/conexiones/{usuario_a}/{usuario_b}` — Responder invitación

Autenticación: **requerida**; solo el destinatario de la invitación.

Body `UpdateConexionSchema`: `estado` debe ser `aceptada` o `rechazada` para una solicitud pendiente.

Respuestas: `200` `GetConexionSchema`; `401` autenticación inválida; `403` no es el destinatario; `404` conexión inexistente; `409` conexión no pendiente o estado no permitido; `422` body/path inválidos.

### `DELETE /api/conexiones/{usuario_id}` — Desconectar

Autenticación: **requerida**.

Elimina únicamente una conexión `aceptada` con el usuario indicado.

Respuestas: `204` sin body; `401` sin autenticación; `404` conexión inexistente; `409` la conexión no está aceptada; `422` path inválido.

## Seguimientos

### `GET /api/usuarios/{usuario_id}/seguimiento` — Consultar seguimiento

Autenticación: **requerida**.

Respuesta `200`: `{"siguiendo": true|false}`; `404` si el usuario destino no existe.

### `POST /api/usuarios/{usuario_id}/seguir` — Seguir usuario

Autenticación: **requerida**.

Respuesta `200`: `SeguimientoResponseSchema` (`seguidor_id`, `seguido_id`, `fecha`). `404` usuario inexistente; `409` si ya se sigue o se intenta seguirse a sí mismo.

### `DELETE /api/usuarios/{usuario_id}/seguir` — Dejar de seguir

Autenticación: **requerida**.

Respuesta `204` sin body. Si no existía el seguimiento, no produce conflicto; `404` solo si el usuario destino no existe.

## Publicaciones y multimedia

Las publicaciones enriquecidas (`GetPublicacionCardSchema`) incluyen `autor`, `reacciones` por tipo, `mi_reaccion`, `cantidad_comentarios` y `multimedia`. Las rutas de archivos devueltas son relativas a `/imagenes` o `/multimedia_publicaciones`.

### `GET /api/publicaciones/autor/{usuario_id}` — Publicaciones de un autor

Autenticación: **opcional**.

Path `usuario_id`; query `limit` default `20` máximo `100` y `offset` default `0`. Respuesta `200`: lista de `GetPublicacionCardSchema`; `401` si se envía un Bearer inválido; `404` si el autor no existe.

### `POST /api/publicaciones` — Crear publicación de texto

Autenticación: **requerida**.

Body `CreatePublicacionSchema`: `texto`, de 1 a 3000 caracteres después de normalizar espacios.

Respuestas: `201` `GetPublicacionSchema`; `401` sin autenticación; `422` body inválido.

### `POST /api/publicaciones/multimedia` — Crear publicación con multimedia

Autenticación: **requerida**. Content-Type: `multipart/form-data`.

Campos:

- `texto` opcional, default vacío, máximo 3000 caracteres.
- `archivos` opcional y repetible: JPG/JPEG/PNG/WEBP, MP4 o WEBM.

Límites actuales: máximo 10 archivos, 150 MiB totales, 5 MiB por imagen y 50 MiB por video. Debe existir texto válido o al menos un archivo; el texto formado únicamente por whitespace se rechaza. Para una publicación solo multimedia se envía el campo `texto` vacío o se omite, y se persiste `texto` como cadena vacía, nunca `null`. Respuestas: `201` `GetPublicacionSchema`; `400` archivo o contenido inválido; `401` sin autenticación; `422` formulario inválido.

### `GET /api/publicaciones/{publicacion_id}` — Detalle de publicación

Autenticación: **requerida**.

Respuesta `200`: `GetPublicacionCardSchema`; `401` autenticación ausente o inválida; `404` publicación inexistente; `422` path inválido.

### `PUT /api/publicaciones/{publicacion_id}` — Editar texto

Autenticación: **requerida**, solo el autor.

Body `UpdatePublicacionSchema`: `texto` opcional (1 a 3000) o `null`. Si se omite, no se modifica. Si se envía `null`, se transforma en texto vacío y solo es válido si la publicación conserva al menos un elemento multimedia; sin multimedia se devuelve `400`. El texto solo whitespace no es válido.

Respuestas: `200` `GetPublicacionSchema`; `400` la publicación quedaría sin texto ni multimedia; `401` sin autenticación; `403` no es el autor; `404` publicación inexistente; `422` body/path inválidos.

### `PUT /api/publicaciones/{publicacion_id}/multimedia` — Editar texto y multimedia

Autenticación: **requerida**, solo el autor. Content-Type: `multipart/form-data`.

Campos:

- `texto`: máximo 3000 caracteres; puede quedar vacío si se conserva o agrega multimedia.
- `conservar_multimedia_id`: lista repetible de IDs existentes que se mantienen.
- `archivos`: archivos nuevos permitidos; mismos límites que en la creación.

La suma de archivos conservados y nuevos no puede superar 10. Respuestas: `200` `GetPublicacionSchema`; `400` selección duplicada, límites o archivo inválido; `401` sin autenticación; `403` archivo de otra publicación o no es el autor; `404` publicación inexistente; `422` formulario/path inválido.

### `DELETE /api/publicaciones/{publicacion_id}` — Eliminar publicación

Autenticación: **requerida**, solo el autor.

Respuesta `204` sin body; `401` sin autenticación; `403` no es el autor; `404` publicación inexistente.

## Feed

### `GET /api/feed` — Feed propio

Autenticación: **requerida**.

Query: `cursor` opcional (máximo 65536), `page_size` default `20` máximo `50`, `exclude_publicacion_id` opcional. Respuesta `200`: `FeedPageSchema` (`items`, `next_cursor`, `has_more`); `400` cursor/filtro inválido; `401` sin autenticación.

### `GET /api/usuarios/{usuario_id}/feed` — Feed de un usuario

Autenticación: **opcional**.

Mismos query parameters que `/api/feed`. Respuesta `200`: `FeedPageSchema`; `400` cursor inválido; `401` si se envía un Bearer inválido; `404` usuario inexistente. Con autenticación, `mi_reaccion` se calcula para el viewer.

## Reacciones

Tipos válidos: `like`, `celebrar`, `apoyar`, `interesante`.

### `POST /api/reacciones` — Crear reacción

Autenticación: **requerida**.

Body `CreateReaccionSchema`: `publicacion_id` y `tipo`.

Respuestas: `201` `GetReaccionSchema`; `401` sin autenticación; `404` publicación inexistente; `409` ya existe una reacción del usuario para esa publicación; `422` body inválido.

### `PATCH /api/publicaciones/{publicacion_id}/reacciones` — Cambiar reacción

Autenticación: **requerida**.

Body `UpdateReaccionSchema`: nuevo `tipo`. Respuesta `200` `GetReaccionSchema`; `401` sin autenticación; `404` publicación o reacción propia inexistente; `422` body/path inválidos.

### `GET /api/publicaciones/{publicacion_id}/reacciones/me` — Obtener mi reacción

Autenticación: **requerida**.

Respuesta `200`: `GetReaccionSchema` o `null` si no existe; `404` publicación inexistente; `401` sin autenticación.

### `DELETE /api/publicaciones/{publicacion_id}/reacciones/me` — Eliminar mi reacción

Autenticación: **requerida**.

Respuesta `204` sin body; si no había reacción no produce conflicto; `404` publicación inexistente; `401` sin autenticación.

### `GET /api/publicaciones/{publicacion_id}/reacciones` — Contar reacciones

Autenticación: **pública**.

Respuesta `200`: objeto con claves `like`, `celebrar`, `apoyar` e `interesante`, todas enteras; `404` publicación inexistente.

## Comentarios

Los comentarios y respuestas usan cursor con `limit` default `10` máximo `50`. El contenido admite hasta 1000 caracteres y no puede quedar vacío.

### `POST /api/publicaciones/{publicacion_id}/comentarios` — Crear comentario

Autenticación: **requerida**.

Body `CrearComentarioSchema`: `contenido`.

Respuesta `201`: `GetComentarioSchema` con autor y `cantidad_respuestas`; `400` contenido vacío o demasiado largo; `401` sin autenticación; `404` publicación inexistente; `422` body/path inválidos.

### `GET /api/publicaciones/{publicacion_id}/comentarios` — Listar comentarios raíz

Autenticación: **requerida**.

Query `limit` y `cursor`. Respuesta `200`: `CursorPageSchema[GetComentarioSchema]`; `400` cursor inválido; `404` publicación inexistente; `401` sin autenticación.

### `POST /api/comentarios/{comentario_id}/respuestas` — Responder comentario

Autenticación: **requerida**.

Body `CrearComentarioSchema`. Respuesta `201`: `GetComentarioSchema`; `400` contenido inválido; `404` comentario o publicación inexistente; `401` sin autenticación.

### `GET /api/comentarios/{comentario_id}/respuestas` — Listar respuestas

Autenticación: **requerida**.

Query `limit` y `cursor`. Respuesta `200`: `CursorPageSchema[GetComentarioSchema]`; `400` cursor inválido; `404` comentario o publicación inexistente; `401` sin autenticación.

### `GET /api/publicaciones/{publicacion_id}/comentarios/count` — Contar comentarios

Autenticación: **requerida**.

Respuesta `200`: `CantidadComentariosSchema` (`cantidad`); `401` sin autenticación; `404` publicación inexistente.

### `DELETE /api/comentarios/{comentario_id}` — Eliminar comentario

Autenticación: **requerida**, solo el autor del comentario.

Respuesta `204` sin body; `401` sin autenticación; `403` no es el autor; `404` comentario inexistente.

## Ofertas

### `POST /api/ofertas` — Crear oferta

Autenticación: **requerida**, rol **OWNER** o **RECRUITER** de `empresa_id`.

Body `CreateOfertaSchema`: `empresa_id`, `titulo` (1–200), `descripcion` no vacía y `publicada` opcional (default `false`). Si se crea publicada, se asigna `fecha_publicacion`.

Respuestas: `201` `GetOfertaSchema`; `401` sin autenticación; `403` sin rol gestor; `404` empresa inexistente; `422` body inválido.

### `GET /api/ofertas/publicadas` — Listar ofertas publicadas

Autenticación: **pública**.

Query `q` opcional (filtro parcial de título), `limit` default `20` máximo `50`, `cursor` opcional.

Respuesta `200`: `CursorPageSchema[GetOfertaSchema]`; `400` cursor inválido; `422` query inválida.

### `GET /api/empresas/{empresa_id}/ofertas` — Ofertas de una empresa

Autenticación: **opcional**. Sin JWT solo se muestran ofertas publicadas; OWNER/RECRUITER de la empresa también ve borradores.

Query `limit` default `20` máximo `50`, `cursor` opcional. Respuesta `200`: `CursorPageSchema[GetOfertaSchema]`; `400` cursor inválido; `401` si se envía un Bearer inválido; `404` empresa inexistente.

### `GET /api/ofertas/{oferta_id}` — Obtener oferta

Autenticación: **opcional**. Una oferta no publicada se comporta como inexistente para quien no sea OWNER/RECRUITER de la empresa.

Respuesta `200`: `GetOfertaSchema` (`id`, `empresa_id`, `titulo`, `descripcion`, `publicada`, `fecha_publicacion`); `401` si se envía un Bearer inválido; `404` oferta no existente o no visible.

### `PUT /api/ofertas/{oferta_id}` — Actualizar oferta

Autenticación: **requerida**, rol **OWNER** o **RECRUITER**.

Body `UpdateOfertaSchema`: `titulo`, `descripcion` y `publicada`, todos opcionales. Al pasar de no publicada a publicada se asigna `fecha_publicacion`.

Respuestas: `200` `GetOfertaSchema`; `401` sin autenticación; `403` sin rol gestor; `404` oferta inexistente; `422` body/path inválidos.

### `GET /api/ofertas/{oferta_id}/estadisticas` — Estadísticas de oferta

Autenticación: **requerida**, rol **OWNER** o **RECRUITER**.

Respuesta `200`: `GetOfertaEstadisticasSchema` con `oferta_id`, `total_postulaciones`, `postulaciones_por_estado` y `dias_desde_publicacion`; `401`/`403`/`404` según acceso y existencia.

## Postulaciones

Estados válidos: `nueva`, `vista`, `entrevista`, `contratado`, `rechazada`. Transiciones permitidas: `nueva` → `vista` o `rechazada`; `vista` → `entrevista` o `rechazada`; `entrevista` → `contratado` o `rechazada`.

### `POST /api/postulaciones` — Crear postulación

Autenticación: **requerida**. El usuario postulante se toma exclusivamente de la identidad autenticada mediante JWT Bearer o cookie HttpOnly.

Body `CreatePostulacionSchema`: únicamente `oferta_id`. `usuario_id` no forma parte del contrato público; si un cliente lo envía como campo extra, se rechaza con `422` y nunca puede elegir al postulante.

Respuestas: `201` `GetPostulacionSchema`; `401` sin autenticación; `404` usuario/oferta inexistente; `409` oferta no publicada, usuario ya miembro o postulación duplicada; `422` body inválido.

### `GET /api/ofertas/{oferta_id}/postulaciones` — Postulaciones de una oferta

Autenticación: **requerida**, rol **OWNER** o **RECRUITER** de la empresa.

Query `limit` default `20` máximo `50`, `cursor` opcional. Respuesta `200`: `CursorPageSchema[GetPostulacionSchema]`; `400` cursor inválido; `401`/`403`/`404` según acceso y existencia.

Cada elemento de `GetPostulacionSchema` incluye `postulante` con `id`, `nombre` y `foto_perfil_url`.

### `GET /api/usuarios/{usuario_id}/postulaciones` — Postulaciones propias

Autenticación: **requerida**; `usuario_id` debe ser el usuario autenticado.

Query `oferta_id` opcional, `limit` default `20` máximo `50`, `cursor` opcional. Respuesta `200`: `CursorPageSchema[GetPostulacionSchema]`; `400` cursor inválido; `403` si se consulta otro usuario; `404` usuario inexistente.

### `GET /api/postulaciones/{postulacion_id}` — Obtener postulación

Autenticación: **requerida**. Puede acceder el postulante o un OWNER/RECRUITER de la empresa de la oferta.

Respuesta `200`: `GetPostulacionSchema`; `401` sin autenticación; `403` sin permiso; `404` inexistente.

### `PATCH /api/postulaciones/{postulacion_id}` — Actualizar estado

Autenticación: **requerida**, rol **OWNER** o **RECRUITER**.

Body `UpdatePostulacionSchema`: `estado`. Al pasar a `contratado`, se agrega `COLLABORATOR` al usuario si no era miembro, se despublica la oferta y se genera una notificación.

Respuestas: `200` `GetPostulacionSchema`; `401` sin autenticación; `403` sin rol gestor; `404` postulación/oferta inexistente; `409` transición inválida o conflicto de membresía; `422` body/path inválidos.

## Tablón y promociones

### `POST /api/promociones` — Crear promoción

Autenticación: **requerida**.

Body `CreatePromocionSchema`: `titulo` (1–160) y `descripcion` (1–3000); no pueden ser solo espacios.

Respuestas: `201` `GetPromocionSchema`; `401` sin autenticación; `422` body inválido.

### `GET /api/promociones` — Listar promociones del tablón

Autenticación: **requerida**. Son promociones visibles para usuarios autenticados dentro de Atanes; “públicas” no significa acceso anónimo desde Internet. El usuario autenticado se utiliza para excluir su propia promoción y resolver disponibilidad.

Query `q` opcional por título, `page` default `1`, `page_size` default `10` máximo `50`.

Respuesta `200`: `GetPromocionesPaginadasSchema` (`items`, `page`, `page_size`, `total`); `401` sin autenticación; `422` query inválida.

### `GET /api/promociones/mias` — Listar mis promociones

Autenticación: **requerida**.

Query `limit` default `10` máximo `50`, `cursor` opcional. Respuesta `200`: `CursorPageSchema[GetPromocionSchema]` con propuestas pendientes; `400` cursor inválido; `401` sin autenticación.

### `GET /api/promociones/{promotion_id}/empresas-contratantes` — Empresas disponibles para contratar

Autenticación: **requerida**.

Devuelve empresas del usuario autenticado donde tiene OWNER o RECRUITER y que pueden proponer la contratación. Respuesta `200`: lista de `GetEmpresaContratanteSchema`; `404` promoción inexistente; `409` promoción no disponible o propia; `401` sin autenticación.

### `POST /api/promociones/{promotion_id}/solicitudes-contratacion` — Crear propuesta

Autenticación: **requerida**, el solicitante debe ser OWNER o RECRUITER de la empresa enviada.

Body `CreateSolicitudContratacionPromocionSchema`: `empresa_id`.

Respuestas: `201` `GetSolicitudContratacionPromocionSchema` en estado `PENDIENTE`; `401` sin autenticación; `403` sin rol gestor; `404` promoción o empresa inexistente; `409` promoción no disponible, candidato ya miembro, propuesta pendiente existente o contratación propia; `422` body/path inválidos.

### `POST /api/solicitudes-contratacion-promocion/{request_id}/aceptar` — Aceptar propuesta

Autenticación: **requerida**; solo el autor de la promoción destinatario de la propuesta.

Sin body. Respuestas: `200` `GetSolicitudContratacionPromocionSchema` en estado `ACEPTADA`; `401` sin autenticación; `403` propuesta dirigida a otro usuario; `404` propuesta o empresa inexistente; `409` propuesta ya respondida o conflicto de membresía.

## Conversaciones y mensajes

Las conversaciones son uno a uno y existe como máximo una por par de usuarios. Para abrir o enviar mensajes se requiere una conexión aceptada; la participación se valida en las operaciones privadas.

### `GET /api/conversaciones` — Listar contactos y conversaciones

Autenticación: **requerida**.

Respuesta `200`: lista de `ContactoConversacionSchema`, incluyendo contactos sin conversación, último mensaje, `no_leidos` y `conectados`; `401` sin autenticación.

### `POST /api/conversaciones` — Abrir o recuperar conversación

Autenticación: **requerida**.

Body `CrearConversacionSchema`: `usuario_id` del otro usuario. Respuesta `200`: `ConversacionSchema` (`id`, `usuario_id`, `fecha_creacion`); `400` auto-conversación; `401` sin autenticación; `403` no existe conexión aceptada; `404` usuario inexistente.

### `GET /api/conversaciones/no-leidos/count` — Contar mensajes no leídos

Autenticación: **requerida**.

Respuesta `200`: `MensajesNoLeidosSchema` (`cantidad`); `401` sin autenticación.

### `GET /api/conversaciones/{conversacion_id}/mensajes` — Listar mensajes

Autenticación: **requerida**, el usuario debe ser participante.

Query `limit` default `30` máximo `100`, `offset` default `0`. Respuesta `200`: lista de `MensajeSchema`; `401` sin autenticación; `403` conversación ajena; `404` conversación inexistente.

### `POST /api/conversaciones/{conversacion_id}/mensajes` — Enviar mensaje

Autenticación: **requerida**, participante de una conversación entre conexiones aceptadas.

Body `EnviarMensajeSchema`: `contenido` no vacío, máximo 2000 caracteres.

Respuestas: `201` `MensajeSchema` con `tipo` de mensaje de texto; `400` contenido vacío o demasiado largo; `401` sin autenticación; `403` conversación ajena o conexión ya no aceptada; `404` conversación inexistente; `422` body/path inválidos.

### `POST /api/conversaciones/{conversacion_id}/mensajes/publicaciones` — Compartir publicación

Autenticación: **requerida**, participante.

Body `CompartirPublicacionSchema`: `publicacion_id` existente. Respuestas: `201` `MensajeSchema` con `tipo` `PUBLICACION`; `401` sin autenticación; `403` conversación ajena o conexión ya no aceptada; `404` conversación o publicación inexistente.

### `POST /api/conversaciones/{conversacion_id}/leer` — Marcar conversación como leída

Autenticación: **requerida**, participante.

Sin body. Respuesta `204` sin body; `401` sin autenticación; `403` conversación ajena; `404` conversación inexistente.

## Notificaciones

Los tipos actuales son `POSTULACION_NUEVA`, `POSTULACION_ESTADO`, `NUEVO_SEGUIDOR`, `NUEVA_INVITACION_CONEXION`, `CONEXION_ACEPTADA` y `CONTRATACION_PROMOCION`. Los mensajes privados no generan notificaciones.

### `GET /api/notificaciones` — Listar notificaciones

Autenticación: **requerida**.

Query `limit` default `30` máximo `100`, `offset` default `0`. Respuesta `200`: lista de `NotificacionResponseSchema`; `401` sin autenticación.

### `GET /api/notificaciones/no-leidas/count` — Contar no leídas

Autenticación: **requerida**.

Respuesta `200`: `NotificacionesNoLeidasSchema` (`cantidad`); `401` sin autenticación.

### `PATCH /api/notificaciones/{notificacion_id}/leida` — Marcar como leída

Autenticación: **requerida**; solo el dueño de la notificación.

Respuesta `200`: `NotificacionResponseSchema` con `leida=true`; `401` sin autenticación; `403` notificación de otro usuario; `404` inexistente.

## Ubicaciones y autocomplete

### `GET /api/ubicaciones/ciudades` — Buscar ciudades

Autenticación: **pública**.

Query: `q` requerido de 2 a 100 caracteres; `limit` default `10`, máximo `15`.

Respuesta `200`: lista de `CiudadSchema` (`pais`, `ciudad`, `nombre`); `422` query inválida. La validación de que una ciudad sea seleccionable se aplica al crear o actualizar un perfil.

## Recursos estáticos de multimedia

Estos mounts de FastAPI sirven archivos almacenados por el backend y no son operaciones de un router, por lo que no aparecen como operaciones en OpenAPI:

- `GET /imagenes/{filename}`: imágenes de perfiles de usuarios y empresas. Las URLs se devuelven en `foto_perfil_url`.
- `GET /multimedia_publicaciones/{filename}`: imágenes y videos de publicaciones. Las rutas se devuelven en `multimedia[].ruta`.

No requieren un JWT adicional. Un archivo inexistente devuelve el error estándar de `StaticFiles`.

## Observaciones del contrato actual

- Las publicaciones solo multimedia persisten `texto=""` porque la columna `publicacion.texto` sigue siendo `NOT NULL`; el Service valida que siempre haya texto no whitespace o al menos un archivo multimedia antes de crear o actualizar.
- La identidad de una postulación siempre se toma del usuario autenticado. El response sí incluye `usuario_id` para identificar al postulante, pero el request de creación no lo recibe como campo de negocio.
- El `GET /api/promociones` requiere autenticación: “públicas” describe visibilidad dentro del tablón para usuarios de Atanes, no anonimato.

## Health check

### `GET /health`

Autenticación: **pública**. Respuesta `200`: `{"status": "ok"}`.
