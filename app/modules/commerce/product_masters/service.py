from typing import Any, Sequence
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, col, func, select

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.storage.cloudinary_service import cloudinary_service
from app.modules.commerce.product_masters.models import (
    ProductImage,
    ProductMaster,
    ProductMasterExternalLink,
)
from app.modules.commerce.product_masters.repository import ProductMasterRepository
from app.modules.commerce.product_masters.schemas import (
    ProductImageReorderItem,
    ProductImageUpdate,
    ProductMasterExternalLinkReorderItem,
    ProductMasterExternalLinkUpdate,
)
from app.modules.commerce.products.models import Product

ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
}
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "avif"}
MAX_IMAGE_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
VALID_IMAGE_TYPES = {"CATALOG", "REAL", "MARKETING", "BANNER"}


def detect_portal(url: str) -> tuple[str, str]:
    """Clasifica automáticamente el portal y genera una etiqueta amigable."""
    cleaned = (url or "").strip().lower()
    if not cleaned:
        return "OTHER", "Enlace Externo"

    if "amazon.co.uk" in cleaned:
        return "AMAZON", "Amazon UK"
    if "amazon.es" in cleaned:
        return "AMAZON", "Amazon España"
    if "amazon.com.mx" in cleaned:
        return "AMAZON", "Amazon México"
    if "amazon.de" in cleaned:
        return "AMAZON", "Amazon Alemania"
    if "amazon.fr" in cleaned:
        return "AMAZON", "Amazon Francia"
    if "amazon.it" in cleaned:
        return "AMAZON", "Amazon Italia"
    if "amazon.com.au" in cleaned:
        return "AMAZON", "Amazon Australia"
    if "amazon.nl" in cleaned:
        return "AMAZON", "Amazon Países Bajos"
    if "amazon.ca" in cleaned:
        return "AMAZON", "Amazon Canadá"
    if "amazon.co.jp" in cleaned:
        return "AMAZON", "Amazon Japón"
    if "amazon." in cleaned:
        return "AMAZON", "Amazon"
    if "ebay." in cleaned:
        return "EBAY", "eBay"
    if "aliexpress." in cleaned:
        return "ALIEXPRESS", "AliExpress"
    if "alibaba." in cleaned:
        return "ALIBABA", "Alibaba"
    if "walmart." in cleaned:
        return "WALMART", "Walmart"
    if "mercadolibre." in cleaned or "articulo.mercadolibre" in cleaned:
        return "MERCADOLIBRE", "MercadoLibre"
    if "youtube.com" in cleaned or "youtu.be" in cleaned:
        return "YOUTUBE", "YouTube"
    if "tiktok.com" in cleaned:
        return "TIKTOK", "TikTok"
    if any(k in cleaned for k in ("facebook.com", "fb.com", "fb.me", "fb.watch")):
        if "marketplace" in cleaned:
            return "FACEBOOK", "Facebook Marketplace"
        return "FACEBOOK", "Facebook"
    if "instagram.com" in cleaned:
        return "INSTAGRAM", "Instagram"
    if "wa.me" in cleaned or "whatsapp.com" in cleaned:
        return "WHATSAPP", "WhatsApp"
    if "shein." in cleaned:
        return "SHEIN", "SHEIN"
    if "temu." in cleaned:
        return "TEMU", "Temu"

    try:
        domain = urlparse(url).netloc.replace("www.", "")
        label = domain.split(".")[0].capitalize() if domain else "Sitio Oficial"
        return "OTHER", label
    except Exception:
        return "OTHER", "Sitio Oficial"


class ProductMasterService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ProductMasterRepository(session)

    def get_next_item_number(self) -> int:
        """Obtiene el siguiente número de catálogo de forma atómica.

        En PostgreSQL consume la secuencia nativa en memoria (cero riesgo de
        condición de carrera).
        En SQLite (entorno de pruebas) utiliza COALESCE(MAX, 0) + 1.
        """
        bind = self.session.get_bind()
        if bind and bind.dialect.name == "postgresql":
            res = self.session.execute(
                text("SELECT nextval('commerce_product_master_item_number_seq')")
            ).scalar_one()
            return int(res)

        # Fallback seguro para SQLite (test suite)
        max_num = (
            self.session.exec(select(func.max(ProductMaster.item_number))).one() or 0
        )
        return int(max_num) + 1

    def create(
        self,
        data: ProductMaster,
        initial_external_url: str | None = None,
        initial_marketplace_url: str | None = None,
    ) -> ProductMaster:
        # 1. Asignación atómica de item_number por el backend si no viene especificado
        if data.item_number is None or data.item_number <= 0:
            data.item_number = self.get_next_item_number()
        else:
            existing_num = self.repository.get_by_item_number(data.item_number)
            if existing_num:
                raise BadRequestException(
                    f"Ya existe una ficha maestra con el número #{data.item_number} "
                    f"({existing_num.name})"
                )

        # 2. Normalizar code: opcional (código de barras de fábrica o SKU)
        if data.code is not None:
            cleaned_code = data.code.strip()
            data.code = cleaned_code if cleaned_code else None

        if data.code:
            existing_code = self.repository.get_by_code(data.code)
            if existing_code:
                raise BadRequestException(
                    f"El código o código de barras '{data.code}' ya existe "
                    f"({existing_code.name})"
                )

        created = self.repository.create(data)

        # Registrar enlace primario de referencia inicial si vino en creación
        if initial_external_url and initial_external_url.strip():
            url_clean = initial_external_url.strip()
            portal, label = detect_portal(url_clean)
            link = ProductMasterExternalLink(
                product_master_id=created.id,
                url=url_clean,
                portal=portal,
                label=label,
                link_type="REFERENCE",
                is_primary=True,
                is_public=True,
                sort_order=1,
            )
            self.session.add(link)

        # Si se especificó initial_marketplace_url, registrar como enlace de marketplace
        if initial_marketplace_url and initial_marketplace_url.strip():
            mkt_clean = initial_marketplace_url.strip()
            portal, label = detect_portal(mkt_clean)
            mkt_label = label if label != "Sitio Oficial" else "Facebook Marketplace"
            mkt_link = ProductMasterExternalLink(
                product_master_id=created.id,
                url=mkt_clean,
                portal=portal,
                label=mkt_label,
                link_type="MARKETPLACE",
                is_primary=True,
                is_public=True,
                sort_order=1,
            )
            self.session.add(mkt_link)
            if not created.is_published_marketplace:
                created.is_published_marketplace = True
                self.session.add(created)

        if (initial_external_url and initial_external_url.strip()) or (
            initial_marketplace_url and initial_marketplace_url.strip()
        ):
            self.session.commit()
            self.session.refresh(created)

        return created

    def get_by_id(self, id: UUID) -> ProductMaster | None:
        return self.repository.get_by_id(id)

    def get_by_item_number(self, item_number: int) -> ProductMaster | None:
        return self.repository.get_by_item_number(item_number)

    def get_by_code(self, code: str) -> ProductMaster | None:
        return self.repository.get_by_code(code)

    def resolve_by_identifier(self, identifier: str | int) -> ProductMaster | None:
        if isinstance(identifier, int):
            return self.get_by_item_number(identifier)

        raw = str(identifier).strip()
        found = self.get_by_code(raw)
        if found:
            return found

        # Tratar de interpretar como número ("53", "053", "NOV-053", "#53")
        cleaned = raw.upper()
        if cleaned.startswith("NOV-"):
            cleaned = cleaned.replace("NOV-", "")
        elif cleaned.startswith("#"):
            cleaned = cleaned.replace("#", "")

        try:
            num = int(cleaned)
            return self.get_by_item_number(num)
        except ValueError:
            return None

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        category_id: UUID | None = None,
        live_basket_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> Sequence[ProductMaster]:
        filters: list[Any] = []
        if category_id:
            filters.append(ProductMaster.category_id == category_id)
        if live_basket_id:
            filters.append(ProductMaster.live_basket_id == live_basket_id)
        if is_active is not None:
            filters.append(ProductMaster.is_active == is_active)

        return self.repository.get_all(
            offset=offset,
            limit=limit,
            sort_by=sort_by or "item_number",
            sort_order=sort_order,
            search=search,
            extra_filters=filters or None,
        )

    def count(
        self,
        search: str | None = None,
        category_id: UUID | None = None,
        live_basket_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> int:
        filters: list[Any] = []
        if category_id:
            filters.append(ProductMaster.category_id == category_id)
        if live_basket_id:
            filters.append(ProductMaster.live_basket_id == live_basket_id)
        if is_active is not None:
            filters.append(ProductMaster.is_active == is_active)

        return self.repository.count(search=search, extra_filters=filters or None)

    def update(self, id: UUID, data: dict) -> ProductMaster | None:
        # item_number y cover_image_url son de solo lectura en este endpoint:
        # - item_number es inmutable y autogenerado por secuencia
        # - cover_image_url se sincroniza automáticamente desde la galería (/images)
        initial_url = data.pop("external_info_url", None)
        initial_mkt_url = data.pop("marketplace_url", None)
        data.pop("item_number", None)
        data.pop("cover_image_url", None)

        if "code" in data:
            raw_code = data["code"]
            data["code"] = raw_code.strip() if raw_code and raw_code.strip() else None
            if data["code"]:
                existing_c = self.repository.get_by_code(data["code"])
                if existing_c and existing_c.id != id:
                    raise BadRequestException(
                        f"El código o código de barras '{data['code']}' ya está "
                        f"asignado a otra ficha maestra ({existing_c.name})"
                    )

        updated = self.repository.update(id, data)
        if updated and initial_url and initial_url.strip():
            self.add_external_link(
                id, url=initial_url.strip(), link_type="REFERENCE", is_primary=True
            )
        if updated and initial_mkt_url and initial_mkt_url.strip():
            self.add_external_link(
                id,
                url=initial_mkt_url.strip(),
                link_type="MARKETPLACE",
                is_primary=True,
            )
        return updated

    def delete(self, id: UUID) -> bool:
        images = self.get_images(id)
        for img in images:
            if img.public_id:
                cloudinary_service.delete_image(img.public_id)
        return self.repository.delete(id)

    def get_stock_summary(self, master_id: UUID) -> dict[str, int]:
        statement = select(
            func.coalesce(func.sum(Product.available_quantity), 0),
            func.coalesce(func.sum(Product.sold_quantity), 0),
            func.coalesce(func.sum(Product.merma_quantity), 0),
        ).where(Product.master_product_id == master_id)

        result = self.session.exec(statement).first()
        if result:
            avail, sold, merma = result
            return {
                "available": int(avail),
                "sold": int(sold),
                "merma": int(merma),
            }
        return {"available": 0, "sold": 0, "merma": 0}

    # =========================================================================
    # MULTI-FOTOGRAFÍAS Y GESTIÓN MULTIMEDIA (CLOUDINARY)
    # =========================================================================

    def get_images(
        self,
        master_id: UUID,
        image_type: str | None = None,
        product_id: UUID | None = None,
    ) -> Sequence[ProductImage]:
        statement = (
            select(ProductImage)
            .where(ProductImage.product_master_id == master_id)
            .order_by(
                col(ProductImage.sort_order).asc(),
                col(ProductImage.created_at).asc(),
            )
        )
        if image_type:
            statement = statement.where(ProductImage.image_type == image_type.upper())
        if product_id is not None:
            statement = statement.where(ProductImage.product_id == product_id)
        return self.session.exec(statement).all()

    def add_images(
        self,
        master_id: UUID,
        files_data: list[dict[str, Any]],
        image_type: str = "CATALOG",
        is_cover: bool = False,
        product_id: UUID | None = None,
    ) -> list[ProductImage]:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        norm_type = (image_type or "CATALOG").strip().upper()
        if norm_type not in VALID_IMAGE_TYPES:
            raise BadRequestException(
                f"Tipo de imagen '{image_type}' inválido. "
                f"Valores permitidos: {', '.join(sorted(VALID_IMAGE_TYPES))}"
            )

        if product_id:
            prod = self.session.get(Product, product_id)
            if not prod or prod.master_product_id != master_id:
                raise BadRequestException(
                    f"El producto físico {product_id} no pertenece a esta ficha maestra"
                )

        if not files_data:
            raise BadRequestException(
                "No se proporcionaron archivos de imagen para subir"
            )

        # 1. Validación previa de cada archivo
        for f in files_data:
            content = f.get("content", b"")
            content_type = f.get("content_type", "")
            filename = f.get("filename", "")

            if len(content) == 0:
                raise BadRequestException(f"El archivo '{filename}' está vacío")

            if len(content) > MAX_IMAGE_FILE_SIZE_BYTES:
                raise BadRequestException(
                    f"El archivo '{filename}' supera el límite máximo de 10 MB"
                )

            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if (
                content_type not in ALLOWED_IMAGE_MIME_TYPES
                and ext not in ALLOWED_IMAGE_EXTENSIONS
            ):
                raise BadRequestException(
                    f"Formato no permitido para '{filename}': {content_type}. "
                    "Formatos aceptados: JPG, PNG, WEBP, GIF, AVIF"
                )

        # 2. Subida a Cloudinary bajo jerarquía: products/{item_number}/{image_type}
        item_folder = (
            str(master.item_number) if master.item_number is not None else "general"
        )
        target_folder = f"products/{item_folder}/{norm_type.lower()}"

        max_order = (
            self.session.exec(
                select(func.max(ProductImage.sort_order)).where(
                    ProductImage.product_master_id == master_id
                )
            ).one()
            or 0
        )
        current_order = int(max_order)

        existing_cover = self.session.exec(
            select(ProductImage).where(
                ProductImage.product_master_id == master_id,
                ProductImage.is_cover == True,  # noqa: E712
            )
        ).first()
        has_cover = bool(existing_cover or master.cover_image_url)

        created_images: list[ProductImage] = []

        for idx, f in enumerate(files_data):
            current_order += 1
            upload_res = cloudinary_service.upload_image(
                file_bytes=f["content"],
                filename=f["filename"],
                folder=target_folder,
            )

            make_cover = False
            if is_cover and idx == 0:
                make_cover = True
            elif not has_cover and idx == 0:
                make_cover = True

            if make_cover:
                all_current_covers = self.session.exec(
                    select(ProductImage).where(
                        ProductImage.product_master_id == master_id,
                        ProductImage.is_cover == True,  # noqa: E712
                    )
                ).all()
                for c in all_current_covers:
                    c.is_cover = False
                    self.session.add(c)

                master.cover_image_url = upload_res["url"]
                self.session.add(master)
                has_cover = True

            img = ProductImage(
                product_master_id=master.id,
                product_id=product_id,
                url=upload_res["url"],
                public_id=upload_res["public_id"],
                image_type=norm_type,
                title=f.get("title") or f["filename"],
                original_filename=f["filename"],
                file_size_bytes=upload_res.get("bytes"),
                width=upload_res.get("width"),
                height=upload_res.get("height"),
                format=upload_res.get("format"),
                is_cover=make_cover,
                sort_order=current_order,
            )
            self.session.add(img)
            created_images.append(img)

        self.session.commit()
        for img in created_images:
            self.session.refresh(img)

        return created_images

    def set_cover_image(self, master_id: UUID, image_id: UUID) -> ProductImage:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        target_img = self.session.get(ProductImage, image_id)
        if not target_img or target_img.product_master_id != master_id:
            raise NotFoundException("Fotografía no encontrada para esta ficha maestra")

        all_images = self.session.exec(
            select(ProductImage).where(ProductImage.product_master_id == master_id)
        ).all()
        for img in all_images:
            img.is_cover = img.id == image_id
            self.session.add(img)

        master.cover_image_url = target_img.url
        self.session.add(master)
        self.session.commit()
        self.session.refresh(target_img)
        return target_img

    def delete_image(self, master_id: UUID, image_id: UUID) -> bool:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        target_img = self.session.get(ProductImage, image_id)
        if not target_img or target_img.product_master_id != master_id:
            raise NotFoundException("Fotografía no encontrada para esta ficha maestra")

        if target_img.public_id:
            cloudinary_service.delete_image(target_img.public_id)

        was_cover = target_img.is_cover or (master.cover_image_url == target_img.url)

        self.session.delete(target_img)
        self.session.flush()

        if was_cover:
            next_img = self.session.exec(
                select(ProductImage)
                .where(ProductImage.product_master_id == master_id)
                .order_by(
                    col(ProductImage.sort_order).asc(),
                    col(ProductImage.created_at).asc(),
                )
            ).first()
            if next_img:
                next_img.is_cover = True
                master.cover_image_url = next_img.url
                self.session.add(next_img)
            else:
                master.cover_image_url = None
            self.session.add(master)

        self.session.commit()
        return True

    def reorder_images(
        self, master_id: UUID, items: list[ProductImageReorderItem]
    ) -> Sequence[ProductImage]:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        for item in items:
            img = self.session.get(ProductImage, item.id)
            if img and img.product_master_id == master_id:
                img.sort_order = item.sort_order
                self.session.add(img)

        self.session.commit()
        return self.get_images(master_id)

    def update_image(
        self, master_id: UUID, image_id: UUID, data: ProductImageUpdate
    ) -> ProductImage:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        img = self.session.get(ProductImage, image_id)
        if not img or img.product_master_id != master_id:
            raise NotFoundException("Fotografía no encontrada para esta ficha maestra")

        if data.title is not None:
            img.title = data.title.strip() if data.title else None
        if data.image_type is not None:
            norm_type = data.image_type.strip().upper()
            if norm_type not in VALID_IMAGE_TYPES:
                raise BadRequestException(
                    f"Tipo de imagen '{data.image_type}' inválido. "
                    f"Valores permitidos: {', '.join(sorted(VALID_IMAGE_TYPES))}"
                )
            img.image_type = norm_type
        if data.sort_order is not None:
            img.sort_order = data.sort_order

        if data.is_cover is True:
            return self.set_cover_image(master_id, image_id)

        self.session.add(img)
        self.session.commit()
        self.session.refresh(img)
        return img

    # =========================================================================
    # ENLACES EXTERNOS MULTI-PORTAL (AMAZON, EBAY, ALIBABA, ETC.)
    # =========================================================================

    def get_external_links(
        self,
        master_id: UUID,
        only_public: bool = False,
        link_type: str | None = None,
    ) -> Sequence[ProductMasterExternalLink]:
        stmt = select(ProductMasterExternalLink).where(
            ProductMasterExternalLink.product_master_id == master_id
        )
        if only_public:
            stmt = stmt.where(ProductMasterExternalLink.is_public == True)  # noqa: E712
        if link_type:
            stmt = stmt.where(
                ProductMasterExternalLink.link_type == link_type.strip().upper()
            )
        stmt = stmt.order_by(
            col(ProductMasterExternalLink.sort_order).asc(),
            col(ProductMasterExternalLink.created_at).asc(),
        )
        return self.session.exec(stmt).all()

    def add_external_link(
        self,
        master_id: UUID,
        url: str,
        link_type: str = "REFERENCE",
        label: str | None = None,
        is_primary: bool = False,
        is_public: bool = True,
    ) -> ProductMasterExternalLink:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        cleaned_url = (url or "").strip()
        if not cleaned_url or not (
            cleaned_url.startswith("http://") or cleaned_url.startswith("https://")
        ):
            raise BadRequestException(
                "La URL debe ser válida y comenzar con http:// o https://"
            )

        norm_type = (link_type or "REFERENCE").strip().upper()
        if norm_type not in ("REFERENCE", "MARKETPLACE"):
            norm_type = "REFERENCE"

        auto_portal, auto_label = detect_portal(cleaned_url)
        assigned_label = label.strip() if label and label.strip() else auto_label

        existing_links = self.get_external_links(master_id, link_type=norm_type)
        make_primary = is_primary or (len(existing_links) == 0)

        # Determinar siguiente sort_order dentro del mismo tipo
        max_order = max([lnk.sort_order for lnk in existing_links], default=0)

        if make_primary:
            for lnk in existing_links:
                if lnk.is_primary:
                    lnk.is_primary = False
                    self.session.add(lnk)

        new_link = ProductMasterExternalLink(
            product_master_id=master.id,
            url=cleaned_url,
            portal=auto_portal,
            link_type=norm_type,
            label=assigned_label,
            is_primary=make_primary,
            is_public=is_public,
            sort_order=max_order + 1,
        )
        self.session.add(new_link)

        # Sincronizar flag is_published_marketplace al añadir publicación
        if norm_type == "MARKETPLACE" and not master.is_published_marketplace:
            master.is_published_marketplace = True
            self.session.add(master)

        self.session.commit()
        self.session.refresh(new_link)
        return new_link

    def update_external_link(
        self,
        master_id: UUID,
        link_id: UUID,
        data: ProductMasterExternalLinkUpdate,
    ) -> ProductMasterExternalLink:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        link = self.session.get(ProductMasterExternalLink, link_id)
        if not link or link.product_master_id != master_id:
            raise NotFoundException(
                "Enlace externo no encontrado para esta ficha maestra"
            )

        if data.link_type is not None:
            norm_type = data.link_type.strip().upper()
            if norm_type in ("REFERENCE", "MARKETPLACE"):
                link.link_type = norm_type

        if data.url is not None:
            cleaned_url = data.url.strip()
            if not cleaned_url or not (
                cleaned_url.startswith("http://") or cleaned_url.startswith("https://")
            ):
                raise BadRequestException(
                    "La URL debe ser válida y comenzar con http:// o https://"
                )
            link.url = cleaned_url
            auto_portal, auto_label = detect_portal(cleaned_url)
            link.portal = auto_portal
            if data.label is None:
                link.label = auto_label

        if data.label is not None:
            link.label = data.label.strip() if data.label else None

        if data.is_public is not None:
            link.is_public = data.is_public

        if data.sort_order is not None:
            link.sort_order = data.sort_order

        if data.is_primary is True:
            return self.set_primary_external_link(master_id, link_id)

        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link

    def set_primary_external_link(
        self, master_id: UUID, link_id: UUID
    ) -> ProductMasterExternalLink:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        target_link = self.session.get(ProductMasterExternalLink, link_id)
        if not target_link or target_link.product_master_id != master_id:
            raise NotFoundException(
                "Enlace externo no encontrado para esta ficha maestra"
            )

        # Desactivar is_primary solo para los enlaces del MISMO link_type
        all_links = self.session.exec(
            select(ProductMasterExternalLink).where(
                ProductMasterExternalLink.product_master_id == master_id,
                ProductMasterExternalLink.link_type == target_link.link_type,
            )
        ).all()

        for lnk in all_links:
            lnk.is_primary = lnk.id == link_id
            self.session.add(lnk)

        self.session.commit()
        self.session.refresh(target_link)
        return target_link

    def delete_external_link(self, master_id: UUID, link_id: UUID) -> bool:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        target_link = self.session.get(ProductMasterExternalLink, link_id)
        if not target_link or target_link.product_master_id != master_id:
            raise NotFoundException(
                "Enlace externo no encontrado para esta ficha maestra"
            )

        was_primary = target_link.is_primary
        link_type = target_link.link_type

        self.session.delete(target_link)
        self.session.flush()

        if was_primary:
            next_link = self.session.exec(
                select(ProductMasterExternalLink)
                .where(
                    ProductMasterExternalLink.product_master_id == master_id,
                    ProductMasterExternalLink.link_type == link_type,
                )
                .order_by(
                    col(ProductMasterExternalLink.sort_order).asc(),
                    col(ProductMasterExternalLink.created_at).asc(),
                )
            ).first()
            if next_link:
                next_link.is_primary = True
                self.session.add(next_link)

        self.session.commit()
        return True

    def reorder_external_links(
        self, master_id: UUID, items: list[ProductMasterExternalLinkReorderItem]
    ) -> Sequence[ProductMasterExternalLink]:
        master = self.get_by_id(master_id)
        if not master:
            raise NotFoundException(f"Ficha maestra {master_id} no encontrada")

        for item in items:
            link = self.session.get(ProductMasterExternalLink, item.id)
            if link and link.product_master_id == master_id:
                link.sort_order = item.sort_order
                self.session.add(link)

        self.session.commit()
        return self.get_external_links(master_id)
