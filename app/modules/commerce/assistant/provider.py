from dataclasses import dataclass

import httpx2
import structlog

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    InternalServerErrorException,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ProviderEndpoint:
    name: str
    url: str
    default_model: str


SUPPORTED_PROVIDERS: dict[str, ProviderEndpoint] = {
    "groq": ProviderEndpoint(
        name="groq",
        url="https://api.groq.com/openai/v1/chat/completions",
        default_model=settings.GROQ_MODEL or "openai/gpt-oss-120b",
    ),
    "mistral": ProviderEndpoint(
        name="mistral",
        url="https://api.mistral.ai/v1/chat/completions",
        default_model=settings.MISTRAL_MODEL or "ministral-8b-latest",
    ),
    "gemini": ProviderEndpoint(
        name="gemini",
        url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        default_model=settings.GEMINI_MODEL or "gemini-3.5-flash",
    ),
}


def get_provider_api_key(provider_name: str) -> str | None:
    """Obtiene la API key configurada para el proveedor."""
    provider = provider_name.lower().strip()
    if provider == "groq":
        return settings.GROQ_API_KEY
    elif provider == "mistral":
        return settings.MISTRAL_API_KEY
    elif provider == "gemini":
        return settings.GEMINI_API_KEY
    return None


def get_configured_providers() -> list[str]:
    """Lista los proveedores que tienen una API key configurada no vacía."""
    configured: list[str] = []
    for prov in ("groq", "mistral", "gemini"):
        key = get_provider_api_key(prov)
        if key and key.strip() and not key.startswith("your_"):
            configured.append(prov)
    return configured


def call_llm(
    messages: list[dict[str, str]],
    requested_provider: str | None = None,
    requested_model: str | None = None,
    enable_fallback: bool | None = None,
) -> tuple[str, str, str, bool]:
    """Envía los mensajes al LLM configurado.

    Implementa conmutación dinámica y fallback automático ante fallos.

    Returns:
        tuple[reply_text, provider_used, model_used, fallback_occurred]
    """
    primary_provider = (
        (requested_provider or settings.AI_DEFAULT_PROVIDER or "groq").lower().strip()
    )
    if primary_provider not in SUPPORTED_PROVIDERS:
        opts = list(SUPPORTED_PROVIDERS.keys())
        raise BadRequestException(
            f"Proveedor '{primary_provider}' no soportado. Válidos: {opts}"
        )

    allow_fallback = (
        enable_fallback if enable_fallback is not None else settings.AI_ENABLE_FALLBACK
    )

    provider_queue: list[str] = [primary_provider]
    if allow_fallback:
        for prov in ("groq", "mistral", "gemini"):
            if prov != primary_provider and prov not in provider_queue:
                provider_queue.append(prov)

    errors_encountered: list[str] = []
    fallback_occurred = False

    for prov_name in provider_queue:
        endpoint = SUPPORTED_PROVIDERS[prov_name]
        api_key = get_provider_api_key(prov_name)

        if not api_key or not api_key.strip() or api_key.startswith("your_"):
            logger.debug(
                "Skipping provider: no API key",
                provider=prov_name,
            )
            continue

        model = (
            requested_model
            if (prov_name == primary_provider and requested_model)
            else endpoint.default_model
        )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2500,
        }

        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        }

        try:
            logger.info("Calling LLM provider", provider=prov_name, model=model)
            with httpx2.Client(timeout=30.0) as client:
                response = client.post(endpoint.url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise ValueError(f"Respuesta vacía de {prov_name}: {data}")
                reply = choices[0]["message"]["content"]
                return (
                    reply,
                    prov_name,
                    model,
                    fallback_occurred,
                )
            else:
                err_msg = (
                    f"[{prov_name}] Error {response.status_code}: {response.text[:200]}"
                )
                logger.warning(
                    "LLM provider error status",
                    provider=prov_name,
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                errors_encountered.append(err_msg)
                fallback_occurred = True

        except Exception as exc:
            err_msg = f"[{prov_name}] Excepción: {str(exc)}"
            logger.warning(
                "Exception calling LLM provider",
                provider=prov_name,
                error=str(exc),
            )
            errors_encountered.append(err_msg)
            fallback_occurred = True

    configured = get_configured_providers()
    if not configured:
        raise BadRequestException(
            "No se ha configurado ninguna API Key válida para los proveedores. "
            "Define GROQ_API_KEY, MISTRAL_API_KEY o GEMINI_API_KEY en .env."
        )

    raise InternalServerErrorException(
        "No se pudo completar la consulta con los proveedores configurados. "
        + " | ".join(errors_encountered)
    )
