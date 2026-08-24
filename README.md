# LinkedIn simplificado

Clon educativo y simplificado de LinkedIn con una API REST en FastAPI, persistencia en PostgreSQL y una interfaz web construida con Next.js y React.

El repositorio está dividido en dos aplicaciones independientes:

- `backend/`: autenticación, reglas de negocio, autorización y acceso a PostgreSQL.
- `frontend/`: interfaz App Router, sesión del usuario y consumo centralizado de la API.

## Funcionalidades

### Usuarios y perfiles

- Registro, login y logout.
- JWT mediante cookie HttpOnly, con soporte alternativo para Bearer tokens.
- Consulta y edición del perfil propio.
- Foto de perfil y fallback visual cuando no existe una imagen.
- Cambio de contraseña verificando la contraseña actual.
- Búsqueda de personas y sugerencias de segundo grado.
- Experiencias laborales asociadas a empresas.

### Red profesional

- Solicitudes de conexión entre usuarios.
- Invitaciones recibidas, aceptación y rechazo.
- Conexiones aceptadas usadas como contactos.
- Seguimiento y dejar de seguir usuarios.
- Resumen de invitaciones enviadas, contactos y seguidos.

### Publicaciones

- Creación, edición y eliminación por el autor.
- Feed paginado con prioridad para publicaciones de usuarios seguidos.
- Consulta de publicaciones por autor.
- Reacciones `like`, `celebrar`, `apoyar` e `interesante`.

### Empresas

- Directorio, búsqueda, creación y consulta de empresas.
- Edición de datos y logo por un OWNER.
- Listado de las empresas a las que pertenece el usuario.
- Gestión de miembros desde `Administrar → Personas de la empresa`.
- Roles `OWNER`, `RECRUITER` y `COLLABORATOR`.

### Empleos y postulaciones

- Creación y actualización de ofertas por OWNER o RECRUITER.
- Publicación y despublicación de ofertas.
- Listado de ofertas publicadas y búsqueda parcial por título, sin distinguir mayúsculas.
- Postulaciones con estados `nueva`, `vista`, `entrevista`, `contratado` y `rechazada`.
- Gestión de postulantes y estadísticas privadas para OWNER o RECRUITER.
- Alta automática como `COLLABORATOR` cuando una postulación pasa a `contratado`, sin degradar una membresía previa.

### Mensajes privados

- Conversaciones privadas uno a uno entre conexiones aceptadas.
- Una única conversación por par de usuarios.
- Lista de todos los contactos, incluso si todavía no hubo mensajes.
- Búsqueda local, parcial y case-insensitive por nombre.
- Historial paginado, borradores y ventanas minimizables/restaurables.
- Actualización mediante polling cada 5 segundos.
- Lectura basada en `conversacion_usuario.ultima_lectura`.
- Indicadores verdes por conversación y en el dock general cuando existen mensajes sin leer.

### Notificaciones

- Nuevas postulaciones.
- Cambios de estado de postulaciones.
- Nuevos seguidores.
- Invitaciones de conexión.
- Conexiones aceptadas.

Mensajes y Notificaciones son sistemas independientes. Enviar un mensaje no crea registros en la tabla ni en la pantalla de notificaciones.

## Stack tecnológico

### Backend

- Python.
- FastAPI `0.115.0` y Uvicorn `0.32.0`.
- SQLAlchemy `2.0.36`.
- PostgreSQL mediante `psycopg2-binary 2.9.10`.
- Pydantic `2.9.2` y `pydantic-settings 2.6.1`.
- JWT con `python-jose 3.3.0`.

Las versiones completas están fijadas en `backend/requirements.txt`.

### Frontend

- Next.js `16.2.4` con App Router.
- React y React DOM `19.2.4`.
- TypeScript `^5`.
- CSS global y Tailwind CSS `^4` como dependencia de desarrollo.

Las versiones completas están en `frontend/package.json` y `frontend/package-lock.json`.

## Arquitectura

El backend sigue el flujo obligatorio:

```text
Router → Service → Repository → PostgreSQL
```

- Los Routers definen el contrato HTTP y las dependencias de FastAPI.
- Los Services concentran reglas de negocio, autorización y coordinación transaccional.
- Los Repositories contienen las consultas SQLAlchemy y la persistencia.
- Los Models representan las tablas SQLAlchemy.
- Los Schemas Pydantic validan entradas y salidas HTTP.
- Los DTOs transportan datos entre capas.
- Los Mappers convierten entre schemas, DTOs y models.

Las consultas SQLAlchemy deben permanecer en Repository. En el frontend, todas las peticiones REST se centralizan en `frontend/lib/api.ts`, que usa `NEXT_PUBLIC_API_URL` y `credentials: "include"`.

## Estructura del repositorio

```text
Linkedin/
├── README.md
├── iniciar_proyecto.bat
├── referencias_frontend/
├── backend/
│   ├── AGENTS.md
│   ├── .env.example
│   ├── requirements.txt
│   ├── scripts/
│   │   └── seed_test_data.py
│   ├── src/
│   │   ├── app.py
│   │   ├── main.py
│   │   ├── config/
│   │   ├── db/
│   │   │   ├── connection.py
│   │   │   ├── models/
│   │   │   ├── migrations/
│   │   │   └── tables.sql
│   │   ├── routers/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── dtos/
│   │   ├── mappers/
│   │   ├── middlewares/
│   │   └── utils/
│   └── tests/
└── frontend/
    ├── AGENTS.md
    ├── .env.example
    ├── package.json
    ├── next.config.ts
    ├── app/
    ├── components/
    ├── lib/
    │   └── api.ts
    └── public/
```

`README.md` explica cómo entender, instalar y ejecutar el proyecto. Los archivos `frontend/AGENTS.md` y `backend/AGENTS.md` contienen reglas operativas para agentes que modifiquen cada aplicación.

## Requisitos previos

- Python compatible con las dependencias de `backend/requirements.txt`.
- Node.js y npm compatibles con Next.js 16.
- PostgreSQL accesible desde el backend.

## Variables de entorno

No se deben versionar secretos reales. Copiá los archivos de ejemplo y ajustá los valores para tu entorno.

### Backend

Desde `backend/`, crear `.env` a partir de `.env.example`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/Linkedin
PORT=8000
JWT_SECRET=cambiar-por-un-secreto-largo-y-aleatorio
FRONTEND_ORIGIN=http://localhost:3000
ENVIRONMENT=development
# COOKIE_SECURE=false
```

`COOKIE_SECURE` es opcional. Si no se define, se activa automáticamente cuando `ENVIRONMENT=production`.

### Frontend

Desde `frontend/`, crear `.env.local` a partir de `.env.example`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Base de datos

El proyecto usa PostgreSQL. No hay un entorno activo de Alembic ni un comando automático de migración, aunque la dependencia figure en `requirements.txt`.

Para una base nueva:

1. Crear una base PostgreSQL, por ejemplo `Linkedin`.
2. Configurar `DATABASE_URL` en `backend/.env`.
3. Ejecutar una sola vez el esquema completo:

```bash
cd backend
psql -U postgres -d Linkedin -f src/db/tables.sql
```

`tables.sql` representa el esquema completo actual. Los archivos de `backend/src/db/migrations/` son cambios SQL incrementales destinados a bases existentes; deben revisarse y aplicarse en orden cuando corresponda, no volver a ejecutarse indiscriminadamente sobre una base ya actualizada.

Opcionalmente, se pueden cargar datos de desarrollo con el script idempotente:

```bash
cd backend
python scripts/seed_test_data.py
```

## Instalación y ejecución

### Backend

```bash
cd backend
python -m venv .venv
```

Activación del entorno:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux o macOS
source .venv/bin/activate
```

Instalación y ejecución:

```bash
pip install -r requirements.txt
python -m src.main
```

También se puede iniciar directamente con:

```bash
python -m uvicorn src.app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

En Windows también se puede usar `npm.cmd run dev`.

URLs locales:

- Frontend: <http://localhost:3000>
- Backend: <http://localhost:8000>
- Swagger/OpenAPI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

En Windows, `iniciar_proyecto.bat` abre backend y frontend en terminales separadas una vez instaladas las dependencias y configurados los `.env`.

## Acceso desde otra computadora de la red

Exponer el frontend:

```powershell
cd frontend
npm.cmd run dev -- --hostname 0.0.0.0
```

Exponer el backend:

```bash
cd backend
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
```

Después hay que configurar, sin hardcodear una IP en el código:

- `NEXT_PUBLIC_API_URL=http://<IP_LOCAL>:8000`
- `FRONTEND_ORIGIN=http://<IP_LOCAL>:3000`
- Las reglas del firewall para los puertos utilizados.

Next.js debe reiniciarse después de cambiar `NEXT_PUBLIC_API_URL`.

## Roles de empresa

### OWNER

Puede editar la empresa y su logo, administrar miembros y roles, crear o actualizar ofertas, publicar/despublicar, gestionar postulaciones y consultar estadísticas privadas. La creación de una empresa asigna automáticamente OWNER al creador.

### RECRUITER

Puede gestionar ofertas, postulaciones y estadísticas de las empresas donde tiene ese rol. No puede editar los datos o el logo de la empresa ni administrar miembros.

### COLLABORATOR

Representa únicamente pertenencia a la empresa. No concede permisos administrativos. Puede asignarse manualmente por un OWNER o automáticamente cuando una postulación pasa a `contratado`. La contratación no reemplaza ni degrada un rol OWNER o RECRUITER existente.

## API

Los endpoints están bajo `/api` y se agrupan por dominios:

- `/api/auth` y `/api/usuarios`
- `/api/conexiones` y seguimiento bajo `/api/usuarios/{id}`
- `/api/publicaciones`, `/api/feed` y reacciones
- `/api/empresas`, `/api/ofertas` y `/api/postulaciones`
- `/api/conversaciones`
- `/api/notificaciones`

La referencia completa y los schemas interactivos se consultan en `/docs`; el README no intenta duplicar Swagger.

## Validación

Backend, desde `backend/`:

```bash
python -m unittest discover -s tests -v
```

Frontend, desde `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
```

En sistemas Unix se puede reemplazar `npm.cmd` por `npm`.
