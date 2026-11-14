from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class MatchedProductContext(BaseModel):
    item_number: int | None = None
    name: str
    brand: str | None = None
    model: str | None = None
    available_stock: int = 0
    sold_stock: int = 0
    official_price: float = 0.0
    published_price: float | None = None
    minimum_price: float = 0.0
    currency: str = "BOB"
    features: str | None = None
    description: str | None = None


class ChatAssistantRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Pregunta del usuario para el asistente",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Historial previo de la conversación en la sesión actual",
    )
    provider: str | None = Field(
        default=None,
        description="Proveedor opcional ('groq', 'mistral', 'gemini')",
    )
    model: str | None = Field(
        default=None,
        description="Modelo específico opcional a consultar",
    )
    include_stock_data: bool = Field(
        default=True,
        description="Si es True, anexa el contexto real de existencias",
    )


class ChatAssistantResponse(BaseModel):
    reply: str
    provider_used: str
    model_used: str
    matched_products: list[MatchedProductContext] = Field(default_factory=list)
    fallback_occurred: bool = False


class ProviderInfoResponse(BaseModel):
    default_provider: str
    configured_providers: list[str]
    all_providers: list[str]
