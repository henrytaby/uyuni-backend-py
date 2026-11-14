from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class MediaUploadResponse(SQLModel):
    url: str = Field(description="URL pública y segura de la imagen optimizada (HTTPS)")
    public_id: str = Field(
        description="Identificador público del archivo en Cloudinary"
    )
    format: str = Field(description="Formato de la imagen (ej: webp, jpg, png)")
    bytes: int = Field(description="Tamaño del archivo en bytes")
    width: int = Field(description="Ancho de la imagen en píxeles")
    height: int = Field(description="Alto de la imagen en píxeles")

    model_config = ConfigDict(extra="ignore")  # type: ignore
