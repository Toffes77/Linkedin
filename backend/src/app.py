from fastapi import FastAPI

from src.middlewares.error_middleware import app_error_handler
from src.routers import auth_router, usuario_router, empresa_router, experiencia_router, conexion_router, publicacion_router, reacciones_router, feed_router, oferta_router, postulacion_router
from src.utils.errors import AppError

app = FastAPI(title="Initial Structure API")

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


@app.get("/health")
def health():
    return {"status": "ok"}
