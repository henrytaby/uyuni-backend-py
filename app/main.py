import time
import uuid
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import FileResponse

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
    internal_server_error_handler,
    not_found_exception_handler,
    unauthorized_exception_handler,
)
from app.core.logging import configure_logging
from app.core.routers import router as api_router

# Setup Logging
configure_logging()

description = """
API de Gestión de Personal y Activos Fijos (ERP Lite).

Funciones:
- Gestión Integral de Personal (Staff) y Unidades Organizacionales.
- Administración y Control de Activos Fijos y Actas de Respaldo.
- Arquitectura Modular Robusta con Auditoría y RBAC.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    register_audit_hooks(engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description=description,
    version=settings.VERSION,
    redoc_url=None,  # Disable default Redoc to customize CDN
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    contact={
        "name": "Henry Alejandro Taby Zenteno",
        "url": "https://github.com/henrytaby",
        "email": "henry.taby@gmail.com",
    },
    openapi_tags=[
        {
            "name": "Auth",
            "description": "Gestión de Autenticación, Roles y Permisos de Usuario.",
        },
        {
            "name": "Tasks",
            "description": "Sistema de gestión de actividades y tareas operativas.",
        },
        {
            "name": "Core Staff - Personal",
            "description": "Administración del capital humano y datos maestros del personal.",
        },
        {
            "name": "Core Staff - Org Units",
            "description": "Gestión de la estructura organizacional y unidades administrativas.",
        },
        {
            "name": "Core Staff - Positions",
            "description": "Definición y control de cargos y puestos de trabajo.",
        },
        {
            "name": "Assets - Institutions",
            "description": "Registro de entidades gubernamentales y organizaciones externas.",
        },
        {
            "name": "Assets - Areas",
            "description": "Control de ubicaciones físicas y áreas geográficas de inventario.",
        },
        {
            "name": "Assets - Asset Groups",
            "description": "Categorización lógica y contable de los bienes del sistema.",
        },
        {
            "name": "Assets - Asset Statuses",
            "description": "Gestión de estados de conservación y situación legal de activos.",
        },
        {
            "name": "Assets - Acts",
            "description": "Control documental de actas de asignación, entrega y respaldo.",
        },
        {
            "name": "Assets - Fixed Assets",
            "description": "Gestión centralizada de Bienes de Uso, códigos SAF y verificación física.",
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


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
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


app.add_exception_handler(NotFoundException, not_found_exception_handler)  # type: ignore
app.add_exception_handler(BadRequestException, bad_request_exception_handler)  # type: ignore
app.add_exception_handler(UnauthorizedException, unauthorized_exception_handler)  # type: ignore
app.add_exception_handler(ForbiddenException, forbidden_exception_handler)  # type: ignore
app.add_exception_handler(InternalServerErrorException, internal_server_error_handler)  # type: ignore


@app.get("/")
async def read_items():
    return FileResponse("./app/index.html")


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@latest/bundles/redoc.standalone.js",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
