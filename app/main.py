import os
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, cast

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.audit import AuditMiddleware, register_audit_hooks
from app.core.config import settings
from app.core.db import create_db_and_tables, engine
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.handlers import (
    bad_request_exception_handler,
    forbidden_exception_handler,
    integrity_error_handler,
    internal_server_error_handler,
    not_found_exception_handler,
    unauthorized_exception_handler,
)
from app.core.logging import configure_logging
from app.core.manifests import global_manifest_registry
from app.core.routers import router as api_router

# Setup Logging
configure_logging()

description = """
API Transaccional y ERP para Emprendimientos y Comercio Electrónico.

Funciones:
- Gestión Integral de Comercio: SKUs, Fichas Maestras, Lotes y Ventas.
- Control de Usuarios, Cuentas y Accesos Basados en Roles (RBAC).
- Motor de Catálogos Dinámicos de Alto Rendimiento (Bulk Loader).
- Arquitectura Modular Robusta con Auditoría CDC Transversal.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Expose engine via app.state for middleware/endpoints (FastAPI pattern)
    app.state.engine = engine
    create_db_and_tables()
    register_audit_hooks(engine)
    try:
        with Session(app.state.engine) as session:
            global_manifest_registry.sync(session)
    except Exception as exc:
        structlog.get_logger("lifespan").warning(
            "modules_manifest_sync_failed", error=str(exc)
        )
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description=description,
    version=settings.VERSION,
    redoc_url=None,  # Disabled default due to jsdelivr.net being blocked
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    contact={
        "name": "Henry Alejandro Taby Zenteno",
        "url": "https://github.com/henrytaby",
        "email": "henry.taby@gmail.com",
    },
    openapi_tags=[
        {
            "name": "Auth",
            "description": "Autenticación, Tokens JWT, Roles y Sesión Activa.",
        },
        {
            "name": "Core - Users",
            "description": "Cuentas de Usuario, Credenciales y Búsqueda.",
        },
        {
            "name": "Commerce - Products",
            "description": "Catálogo de productos, SKUs NOV-XXX, stock y estados.",
        },
        {
            "name": "Commerce - Product Masters",
            "description": "Fichas maestras de productos, catálogo y especificaciones.",
        },
        {
            "name": "Commerce - Sales",
            "description": "Punto de venta y transacciones atómicas multicanal.",
        },
        {
            "name": "Commerce - Batches & Boxes",
            "description": "Lotes de importación, costos y punto de equilibrio.",
        },
        {
            "name": "Commerce - Categories",
            "description": "Taxonomía oficial de categorías de productos.",
        },
        {
            "name": "Commerce - Sales Channels",
            "description": "Canales comerciales de venta (Tienda, WhatsApp, etc.).",
        },
        {
            "name": "Commerce - Live Baskets",
            "description": "Canastas estratégicas para transmisiones en vivo.",
        },
        {
            "name": "Commerce - Investment Rounds",
            "description": "Control de rondas de inversión y retorno de capital.",
        },
        {
            "name": "Global - Catalogs",
            "description": "Catálogos Dinámicos Modulares y Carga Masiva (Bulk).",
        },
        {
            "name": "Tasks",
            "description": "Sistema de gestión de actividades y tareas operativas.",
        },
        {
            "name": "Health",
            "description": "Monitoreo y verificación del estado del servidor.",
        },
    ],
    openapi_url="/openapi.json",
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los encabezados
)
app.add_middleware(AuditMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def logging_middleware(request: Request, call_next: Callable[[Request], Any]):
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Log Filtering Logic
    should_log = settings.ENABLE_ACCESS_LOGS
    if should_log and settings.ACCESS_LOGS_ONLY_ERRORS:
        should_log = response.status_code >= 400

    if should_log:
        structlog.get_logger("api.access").info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )

    return response


# version_prefix = f"/api/{version}"
version_prefix = "/api"
# Incluir el router principal
app.include_router(api_router, prefix=version_prefix)

# Servir archivos estáticos (logos, assets)
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


app.add_exception_handler(NotFoundException, not_found_exception_handler)  # type: ignore
app.add_exception_handler(BadRequestException, bad_request_exception_handler)  # type: ignore
app.add_exception_handler(UnauthorizedException, unauthorized_exception_handler)  # type: ignore
app.add_exception_handler(ForbiddenException, forbidden_exception_handler)  # type: ignore
app.add_exception_handler(InternalServerErrorException, internal_server_error_handler)  # type: ignore
app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore


@app.get("/")
async def read_items() -> FileResponse:
    return FileResponse("./app/index.html")


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "uyuni-backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    """
    Custom Redoc setup pinning the stable UMD bundle (v2.1.5) on unpkg CDN,
    avoiding the 'import.meta' ESM syntax error introduced in unpkg @latest (v3+).
    """
    return get_redoc_html(
        openapi_url=cast(str, app.openapi_url),
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@2.1.5/bundles/redoc.standalone.js",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
