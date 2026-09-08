from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from src.config.env import settings
from src.middlewares.error_middleware import app_error_handler
from src.routers import auth_router, usuario_router, empresa_router, experiencia_router, conexion_router, publicacion_router, reacciones_router, feed_router, oferta_router, postulacion_router, seguimiento_router, notificacion_router, mensaje_router, comentario_router, promocion_router, ubicacion_router
from src.utils.errors import AppError


OPENAPI_DESCRIPTION = (
    "API REST de Atanes. Los endpoints están agrupados por dominio y usan "
    "la arquitectura Router → Service → Repository → PostgreSQL. "
    "La autenticación acepta el JWT del encabezado Authorization: Bearer "
    "o la cookie HttpOnly access_token emitida por /api/auth/login."
)

OPENAPI_TAGS = [
    {"name": "auth", "description": "Inicio y cierre de sesión."},
    {"name": "usuarios", "description": "Registro, perfiles y búsqueda de personas."},
    {"name": "experiencias", "description": "Experiencias laborales de usuarios."},
    {"name": "ubicaciones", "description": "Autocompletado de ciudades válidas."},
    {"name": "empresas", "description": "Empresas, miembros y roles."},
    {"name": "conexiones", "description": "Invitaciones y conexiones profesionales."},
    {"name": "seguimiento", "description": "Seguimiento de usuarios."},
    {"name": "publicaciones", "description": "Publicaciones y multimedia."},
    {"name": "feed", "description": "Feed personalizado y feeds por usuario."},
    {"name": "reacciones", "description": "Reacciones y conteos de publicaciones."},
    {"name": "comentarios", "description": "Comentarios, respuestas y conteos."},
    {"name": "ofertas", "description": "Ofertas de empleo publicadas y privadas."},
    {"name": "postulaciones", "description": "Postulaciones y sus estados."},
    {"name": "tablón", "description": "Promociones y propuestas de contratación."},
    {"name": "mensajes", "description": "Conversaciones y mensajes privados."},
    {"name": "notificaciones", "description": "Notificaciones de actividad."},
]

app = FastAPI(
    title="Atanes API",
    description=OPENAPI_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMAGES_DIRECTORY = Path(__file__).resolve().parents[1] / "imagenes"
IMAGES_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount("/imagenes", StaticFiles(directory=IMAGES_DIRECTORY), name="imagenes")

PUBLICATION_MEDIA_DIRECTORY = Path(__file__).resolve().parents[1] / "multimedia_publicaciones"
PUBLICATION_MEDIA_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount(
    "/multimedia_publicaciones",
    StaticFiles(directory=PUBLICATION_MEDIA_DIRECTORY),
    name="multimedia_publicaciones",
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(usuario_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(empresa_router.router, prefix="/api")
app.include_router(experiencia_router.router, prefix="/api")
app.include_router(conexion_router.router, prefix="/api")
app.include_router(publicacion_router.router, prefix="/api")
app.include_router(reacciones_router.router, prefix="/api")
app.include_router(feed_router.router, prefix="/api")
app.include_router(oferta_router.router, prefix="/api")
app.include_router(postulacion_router.router, prefix="/api")
app.include_router(seguimiento_router.router, prefix="/api")
app.include_router(notificacion_router.router, prefix="/api")
app.include_router(mensaje_router.router, prefix="/api")
app.include_router(comentario_router.router, prefix="/api")
app.include_router(promocion_router.router, prefix="/api")
app.include_router(ubicacion_router.router, prefix="/api")


@app.get(
    "/health",
    response_model=dict[str, str],
    summary="Comprobar disponibilidad",
    description="Endpoint público de salud del proceso HTTP.",
)
def health():
    return {"status": "ok"}


def custom_openapi():
    """Expose both supported authentication transports in the generated schema."""

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "cookieAuth"
    ] = {
        "type": "apiKey",
        "in": "cookie",
        "name": "access_token",
        "description": "JWT en la cookie HttpOnly access_token creada por /api/auth/login.",
    }
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            security = operation.get("security")
            if security and any("HTTPBearer" in requirement for requirement in security):
                operation["security"] = [{"HTTPBearer": []}, {"cookieAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
