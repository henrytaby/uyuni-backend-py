from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.auth.utils import get_current_user
from app.core.exceptions import BadRequestException
from app.core.storage.cloudinary_service import cloudinary_service
from app.models.user import User
from app.modules.core.media.schemas import MediaUploadResponse

router = APIRouter(prefix="/media", tags=["Media / Storage"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    summary="Subir imagen a Cloudinary (Avatares / Catálogo)",
    description=(
        "Sube y optimiza una imagen a Cloudinary. Soporta carpetas: avatars, products, "
        "categories, general. Convierte y sirve automáticamente en WebP "
        "con compresión inteligente."
    ),
)
async def upload_image(
    file: UploadFile = File(
        ..., description="Archivo de imagen (JPG, PNG, WEBP, GIF, máx 5MB)"
    ),
    folder: Literal["avatars", "products", "categories", "general"] = Query(
        default="avatars",
        description="Carpeta de destino en Cloudinary",
    ),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise BadRequestException(
            detail=(
                f"Tipo de archivo no permitido: {file.content_type}. "
                "Formatos permitidos: JPG, PNG, WEBP, GIF."
            )
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise BadRequestException(
            detail="El archivo excede el tamaño máximo permitido de 5 MB."
        )

    if len(file_bytes) == 0:
        raise BadRequestException(detail="El archivo está vacío.")

    result = cloudinary_service.upload_image(
        file_bytes=file_bytes,
        filename=file.filename,
        folder=folder,
    )
    return result
