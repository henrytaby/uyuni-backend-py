import re
from typing import Any

import cloudinary
import cloudinary.uploader
import structlog

from app.core.config import settings
from app.core.exceptions import BadRequestException, InternalServerErrorException

logger = structlog.get_logger(__name__)


class CloudinaryService:
    def __init__(self) -> None:
        self._configured: bool = False
        self._configure()

    def _configure(self) -> None:
        if (
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET
        ):
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )
            self._configured = True

    def is_configured(self) -> bool:
        if not self._configured:
            self._configure()
        return self._configured

    def upload_image(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        folder: str = "general",
        public_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise BadRequestException(
                detail=(
                    "El servicio de Cloudinary no está configurado "
                    "(faltan credenciales)"
                )
            )

        try:
            target_folder = f"uyuni/{folder}".strip("/")
            upload_params: dict[str, Any] = {
                "folder": target_folder,
                "resource_type": "image",
                "tags": [folder, "uyuni"],
                "transformation": [
                    {"quality": "auto", "fetch_format": "auto"}
                ],
            }

            if public_id:
                upload_params["public_id"] = public_id
                upload_params["overwrite"] = True
            else:
                upload_params["use_filename"] = bool(filename)
                upload_params["unique_filename"] = True

            upload_result = cloudinary.uploader.upload(
                file_bytes,
                **upload_params,
            )
            return {
                "url": upload_result.get("secure_url")
                or upload_result.get("url"),
                "public_id": upload_result.get("public_id"),
                "format": upload_result.get("format"),
                "bytes": upload_result.get("bytes", 0),
                "width": upload_result.get("width", 0),
                "height": upload_result.get("height", 0),
            }
        except Exception as exc:
            logger.error("cloudinary_upload_failed", error=str(exc))
            raise InternalServerErrorException(
                detail=f"Error al subir imagen a Cloudinary: {str(exc)}"
            ) from exc

    def extract_public_id_from_url(self, url: str | None) -> str | None:
        """
        Extrae el public_id de una URL de Cloudinary.
        Ejemplo: https://res.cloudinary.com/novalabs-bo/image/upload/v1234/uyuni/avatars/pic.webp
        Retorna: uyuni/avatars/pic
        """
        if not url or "res.cloudinary.com" not in url:
            return None
        pattern = r"/upload/(?:v\d+/)?(.*?)(?:\.[a-zA-Z0-9]+)?$"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None

    def delete_image(self, public_id: str) -> bool:
        """Elimina un recurso en Cloudinary dado su public_id."""
        if not self.is_configured() or not public_id:
            return False
        try:
            result = cloudinary.uploader.destroy(public_id)
            is_ok = result.get("result") in ("ok", "not found")
            logger.info(
                "cloudinary_image_deleted", public_id=public_id, result=result
            )
            return is_ok
        except Exception as exc:
            logger.warning(
                "cloudinary_delete_failed", public_id=public_id, error=str(exc)
            )
            return False

    def delete_image_by_url(self, url: str | None) -> bool:
        """Extrae el public_id de una URL y elimina la imagen de Cloudinary."""
        public_id = self.extract_public_id_from_url(url)
        if public_id:
            return self.delete_image(public_id)
        return False


cloudinary_service = CloudinaryService()
