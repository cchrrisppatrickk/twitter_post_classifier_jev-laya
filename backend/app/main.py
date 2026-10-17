"""
main.py - Punto de entrada del servidor FastAPI, configuración CORS,
montaje de rutas estáticas y ciclo de vida de la aplicación.
"""

from __future__ import annotations
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import endpoints_batch, endpoints_categories, endpoints_database, endpoints_ingest, endpoints_posts, endpoints_system
from .config import settings
from .database import init_db
from .registry import load_registry_data

logger = logging.getLogger("app_main")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización de BD SQLite WAL y caché taxonómica."""
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}...")
    await init_db()
    load_registry_data()
    logger.info("Sistema listo para aceptar peticiones HTTP y streaming SSE.")
    yield
    logger.info("Cerrando aplicación...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Servidor API REST y Streaming SSE para Clasificación Semántica System 1 y Dashboard Matricial de X.",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de Enrutadores API
app.include_router(endpoints_posts.router)
app.include_router(endpoints_ingest.router)
app.include_router(endpoints_batch.router)
app.include_router(endpoints_system.router)
app.include_router(endpoints_categories.router)
app.include_router(endpoints_database.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Retorna HTTP 204 No Content para silenciar peticiones automáticas de navegadores."""
    return Response(status_code=204)


# Montaje de Archivos Estáticos del Frontend
frontend_path = settings.FRONTEND_DIR
if frontend_path.exists():
    css_path = frontend_path / "css"
    js_path = frontend_path / "js"
    if css_path.exists():
        app.mount("/css", StaticFiles(directory=str(css_path)), name="css")
    if js_path.exists():
        app.mount("/js", StaticFiles(directory=str(js_path)), name="js")
    # Montar carpeta completa bajo /static para assets adicionales
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    templates = Jinja2Templates(directory=str(frontend_path))

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def serve_index(request: Request):
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return templates.TemplateResponse(
                request=request,
                name="index.html"
            )
        return {"message": f"{settings.APP_NAME} API activa. Visite /docs para OpenAPI."}

    @app.api_route("/config", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/config.html", methods=["GET", "HEAD"], include_in_schema=False)
    async def serve_config(request: Request):
        config_file = frontend_path / "config.html"
        if config_file.exists():
            return templates.TemplateResponse(
                request=request,
                name="config.html"
            )
        return {"error": "config.html no encontrado en frontend."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
