from fastapi import APIRouter, Depends

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.config import settings
from app.core.db import SessionDep
from app.modules.commerce.assistant.provider import (
    SUPPORTED_PROVIDERS,
    get_configured_providers,
)
from app.modules.commerce.assistant.schemas import (
    ChatAssistantRequest,
    ChatAssistantResponse,
    ProviderInfoResponse,
)
from app.modules.commerce.assistant.service import CommerceAssistantService
from app.modules.commerce.constants import CommerceModuleSlug

router = APIRouter(prefix="/assistant", tags=["Commerce - AI Assistant"])


@router.post("/chat", response_model=ChatAssistantResponse)
def chat_with_assistant(
    request: ChatAssistantRequest,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
) -> ChatAssistantResponse:
    """Interactúa con el asistente inteligente de catálogo e inventario.

    Busca productos y existencias físicas en tiempo real y consulta al
    proveedor de IA configurado (Groq, Mistral o Gemini) con fallback.
    """
    service = CommerceAssistantService(session)
    return service.handle_chat(request)


@router.get("/providers", response_model=ProviderInfoResponse)
def get_assistant_providers(
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
) -> ProviderInfoResponse:
    """Retorna los proveedores disponibles y con credenciales configuradas."""
    return ProviderInfoResponse(
        default_provider=settings.AI_DEFAULT_PROVIDER,
        configured_providers=get_configured_providers(),
        all_providers=list(SUPPORTED_PROVIDERS.keys()),
    )
