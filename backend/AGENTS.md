# Manual operativo del backend

Este archivo aplica a todo `backend/`. El README de la raíz describe el producto y su instalación; este documento establece cómo modificar la API respetando su arquitectura.

## Antes de editar

1. Ejecutar `git status` desde la raíz del repositorio.
2. No revertir, sobrescribir ni mezclar cambios existentes que no pertenezcan al pedido.
3. Inspeccionar el flujo completo del dominio afectado: router, schema, mapper, DTO, service, repository, model y tests.
4. Revisar `src/db/tables.sql` y las migraciones cuando intervenga persistencia.
5. Limitar el cambio al objetivo solicitado y usar `apply_patch` para editar archivos.

No cambiar contratos, permisos o estructura de datos solamente para facilitar una implementación distinta de la solicitada.

## Arquitectura obligatoria

```text
Router → Service → Repository → PostgreSQL
```

### Router

Responsabilidades:

- Declarar rutas, métodos HTTP, parámetros, query strings y status codes.
- Inyectar la sesión SQLAlchemy y la autenticación mediante dependencias FastAPI.
- Validar el contrato HTTP con Schemas Pydantic.
- Convertir schemas a DTOs y DTOs a schemas mediante Mappers.
- Delegar la operación al Service.

No colocar queries SQLAlchemy, reglas de autorización complejas ni coordinación transaccional directamente en routers.

### Service

Responsabilidades:

- Aplicar reglas de negocio y transiciones de estado.
- Autorizar acciones usando el usuario autenticado.
- Coordinar uno o más repositories.
- Validar existencia, pertenencia y conflictos del dominio.
- Delimitar operaciones atómicas y ejecutar rollback cuando corresponda.

El Service puede consultar a distintos repositories, pero no debe construir queries SQLAlchemy.

### Repository

Responsabilidades:

- Consultar y persistir mediante SQLAlchemy.
- Encapsular filtros, joins, orden, paginación, constraints esperadas y estrategias de carga.
- Ofrecer operaciones con `commit=False` cuando un Service necesite coordinar una transacción mayor, siguiendo los patrones existentes.

No trasladar al Repository decisiones de negocio o permisos que pertenecen al Service.

## Models, Schemas, DTOs y Mappers

El backend separa:

- `src/db/models/`: modelos SQLAlchemy y relaciones.
- `src/schemas/`: entrada y salida HTTP con Pydantic.
- `src/dtos/`: transporte tipado entre capas.
- `src/mappers/`: conversiones Schema ↔ DTO ↔ Model.

Reutilizar esta separación. No devolver Models SQLAlchemy directamente desde routers cuando el dominio ya usa DTOs, schemas y mappers. Mantener `ConfigDict(from_attributes=True)` donde el patrón existente lo requiera.

Los nombres históricos de algunos archivos no son completamente uniformes; antes de crear una variante nueva, buscar el patrón real del dominio relacionado.

## Autenticación y seguridad

- Reutilizar `get_current_user` de `src/middlewares/auth_middleware.py`.
- La identidad autenticada sale del JWT enviado por cookie HttpOnly o encabezado Bearer.
- Bearer tiene precedencia sobre la cookie; no romper ninguno de los dos mecanismos.
- No confiar en `usuario_id`, `autor_id`, `seguidor_id` u otro identificador del body cuando representa al usuario autenticado.
- Comparar siempre el recurso solicitado con `current_user.id` o pasar esa identidad al Service.
- Validar pertenencia antes de leer o modificar recursos privados.
- No exponer `password_hash`, tokens, secretos ni información privada en DTOs de respuesta.
- Mantener CORS con origen configurable y credenciales habilitadas.

Ocultar controles en frontend no sustituye las validaciones de autorización del backend.

## Roles de empresa

Los roles están definidos por `RolEmpresa` y por el enum PostgreSQL `rol_empresa`:

- `OWNER`
- `RECRUITER`
- `COLLABORATOR`

Distinguir dos preguntas:

### Pertenencia

Cuando la regla pregunta si una persona pertenece a una empresa, pueden contar los tres roles. Por ejemplo, `/empresas/me` incluye todas las relaciones.

### Administración

Usar únicamente los roles autorizados por la operación:

- OWNER: edición de empresa y logo, administración de miembros, ofertas, postulaciones y estadísticas.
- RECRUITER: ofertas, postulaciones y estadísticas.
- COLLABORATOR: ninguna acción administrativa.

No reemplazar una comprobación específica por `rol in todos_los_roles`. En particular, `COLLABORATOR` nunca debe incorporarse accidentalmente a validaciones para gestionar empresas, miembros, ofertas, postulaciones o estadísticas.

La empresa debe conservar al menos un OWNER. Contratar a un usuario crea COLLABORATOR solamente si todavía no pertenece a la empresa y nunca degrada OWNER o RECRUITER.

## PostgreSQL y cambios de esquema

- Todas las consultas de aplicación deben implementarse en Repository.
- Mantener sincronizados Models SQLAlchemy, `src/db/tables.sql`, schemas/DTOs relacionados y tests.
- `tables.sql` representa el esquema completo para una base nueva.
- `src/db/migrations/` contiene SQL incremental para actualizar bases existentes.
- El proyecto no tiene actualmente un entorno operativo de Alembic; no inventar comandos o revisiones Alembic sin una tarea explícita que lo incorpore.
- Respetar nombres de tablas, enums, casing, foreign keys, checks, uniques e índices existentes.
- Preferir restricciones de base para invariantes críticas, además de validación en Service.
- No borrar ni recrear tablas con datos para aplicar un cambio incremental.
- No ejecutar DDL contra la base configurada salvo que el usuario lo solicite explícitamente.

Si una tarea autoriza modificar la base real:

1. Confirmar `DATABASE_URL` sin publicar credenciales.
2. Usar SQL idempotente o una migración segura cuando sea posible.
3. No eliminar datos existentes.
4. Verificar tablas, columnas, constraints e índices desde PostgreSQL después del cambio.

## Transacciones

Una operación que modifica varias entidades relacionadas debe ser atómica. Revisar los patrones `commit=False`, `flush`, `commit` final y `rollback` en los Services existentes.

Ejemplos relevantes:

- Crear una postulación y notificar a los responsables.
- Cambiar el estado de una postulación, crear una membresía y notificar al postulante.
- Crear o aceptar una conexión junto con su notificación.
- Seguir a un usuario y crear la notificación asociada.
- Crear una conversación con sus dos participantes.
- Persistir un mensaje y actualizar la fecha del último mensaje.

No dejar commits parciales que permitan guardar la entidad principal sin sus efectos obligatorios.

## Mensajes privados

- Los contactos válidos son conexiones con estado `aceptada`.
- Existe como máximo una conversación por par canonizado de usuarios.
- El autor del mensaje siempre es el usuario autenticado.
- Verificar la participación antes de listar, enviar o marcar lectura.
- Rechazar contenido vacío, solo espacios o superior al máximo vigente.
- Mantener la paginación y el orden cronológico esperado por el frontend.
- Usar `conversacion_usuario.ultima_lectura` como fuente del estado no leído mientras siga siendo la implementación actual.
- Mensajes y Notificaciones son dominios separados. No crear tipos ni filas de notificación por mensajes.

## Errores

Reutilizar las excepciones de `src/utils/errors.py` y el manejador global:

- `BadRequestError`
- `NotFoundError`
- `UnauthorizedError`
- `ForbiddenError`
- `ConflictError`

No devolver estructuras HTTP ad hoc si una excepción existente representa el caso. Mantener mensajes comprensibles sin revelar detalles internos o sensibles.

## Tests

Todo cambio funcional debe agregar o actualizar pruebas proporcionales al riesgo:

- Reglas y autorización en Service.
- Contrato, autenticación y status HTTP en Router.
- Queries, orden, filtros, constraints y persistencia cuando corresponda.
- Transacciones y rollback para operaciones multi-entidad.
- Regresiones de roles, seguridad y aislamiento entre usuarios.

Los tests PostgreSQL existentes usan transacciones para no conservar sus datos. No introducir fixtures que borren tablas o dependan de un estado previo no controlado.

Después de cualquier cambio backend ejecutar la suite completa desde `backend/`:

```bash
python -m unittest discover -s tests -v
```

No ejecutar solo los tests nuevos y asumir que el resto continúa funcionando.

## Lista de control final

- El Router no contiene SQLAlchemy.
- La lógica de negocio y autorización está en Service.
- Las queries están en Repository.
- Models, schemas, DTOs, mappers y SQL están sincronizados.
- La identidad sensible viene de `get_current_user`.
- COLLABORATOR no obtuvo permisos administrativos.
- Las operaciones multi-entidad son atómicas.
- La suite backend completa fue ejecutada.
- `git diff --check` no reporta errores.
