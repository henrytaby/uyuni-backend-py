from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.auth.utils import get_current_user
from app.core.catalogs.registry import global_registry
from app.core.catalogs.schemas import CatalogItemSchema
from app.core.db import get_session

router = APIRouter(prefix="/catalogs", tags=["Global - Catalogs"])


@router.post("/bulk", response_model=dict[str, list[CatalogItemSchema]])
def get_bulk_catalogs(
    request_data: dict[str, dict[str, Any]],
    session: Session = Depends(get_session),
    _=Depends(get_current_user),
):
    """
    Recupera múltiples catálogos en una sola petición HTTP.
    El cuerpo de la petición debe ser un mapa JSON donde las llaves son los nombres
    de los catálogos y los valores son objetos conteniendo los parámetros específicos
    para cada proveedor (por ejemplo: {"departamentos": {"gerencia_id": "..."}}).
    """
    result = {}
    for catalog_name, params in request_data.items():
        provider = global_registry.get_provider(catalog_name)
        result[catalog_name] = provider.get_items(session, **params)
    return result


@router.get("/{catalog_name}", response_model=list[CatalogItemSchema])
def get_single_catalog(
    catalog_name: str,
    request: Request,
    session: Session = Depends(get_session),
    _=Depends(get_current_user),
):
    """
    Recupera un catálogo individual de forma dinámica y genérica.
    """
    provider = global_registry.get_provider(catalog_name)
    return provider.get_items(session, **dict(request.query_params))
