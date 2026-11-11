from sqlmodel import Session, col, select

from app.core.catalogs.base import CatalogProvider
from app.core.catalogs.schemas import CatalogItemSchema
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.categories.models import Category
from app.modules.commerce.channels.models import SalesChannel
from app.modules.commerce.live_baskets.models import LiveBasket
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.rounds.models import InvestmentRound


class CommerceCategoriesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = select(Category.id, Category.name, Category.icon).order_by(
            Category.code
        )
        results = session.exec(query).all()
        return [
            CatalogItemSchema(
                value=r[0],
                label=f"{r[2]} {r[1]}" if r[2] else r[1],
            )
            for r in results
        ]


class CommerceLiveBasketsProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = select(LiveBasket.id, LiveBasket.label).order_by(LiveBasket.code)
        results = session.exec(query).all()
        return [CatalogItemSchema(value=r[0], label=r[1]) for r in results]


class CommerceBatchesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = select(Batch.id, Batch.name, Batch.code).order_by(Batch.name)
        results = session.exec(query).all()
        return [
            CatalogItemSchema(value=r[0], label=f"{r[1]} ({r[2]})") for r in results
        ]


class CommercePhysicalConditionsProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(value="OPERATIONAL", label="Operativo"),
            CatalogItemSchema(value="DAMAGED_SCRAP", label="Dañado / Merma"),
            CatalogItemSchema(value="FOR_PARTS", label="Para Repuestos"),
            CatalogItemSchema(value="INCOMPLETE", label="Incompleto / Sin Caja"),
            CatalogItemSchema(value="REPAIRED", label="Reparado"),
        ]


class CommerceProductStatusesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(value="AVAILABLE", label="Disponible"),
            CatalogItemSchema(value="RESERVED", label="Reservado"),
            CatalogItemSchema(value="SOLD_OUT", label="Vendido / Agotado"),
            CatalogItemSchema(value="SCRAPPED", label="Merma / Baja"),
        ]


class CommerceInvestmentRoundsProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = select(
            InvestmentRound.id, InvestmentRound.name, InvestmentRound.code
        ).order_by(InvestmentRound.code)
        results = session.exec(query).all()
        return [
            CatalogItemSchema(value=r[0], label=f"{r[2]} - {r[1]}") for r in results
        ]


class CommerceSalesChannelsProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = (
            select(SalesChannel.id, SalesChannel.name, SalesChannel.code)
            .where(SalesChannel.is_active == True)  # noqa: E712
            .order_by(SalesChannel.name)
        )
        results = session.exec(query).all()
        return [CatalogItemSchema(value=r[0], label=r[1]) for r in results]


class CommercePaymentStatusesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(value="COLLECTED", label="Cobrado"),
            CatalogItemSchema(value="PENDING", label="Pendiente"),
            CatalogItemSchema(value="COURTESY", label="Cortesía / 0 Bs"),
            CatalogItemSchema(value="REFUNDED", label="Reembolsado / Devolución"),
        ]


class CommerceDeliveryModalitiesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(
                value="FREE_MEETING_POINT", label="Punto de Encuentro Gratis"
            ),
            CatalogItemSchema(value="HOME_DELIVERY", label="Delivery Domicilio"),
            CatalogItemSchema(value="TERMINAL_BUS", label="Envío Flota (Terminal)"),
            CatalogItemSchema(
                value="NATIONAL_COURIER", label="Envío Courier (Nacional)"
            ),
            CatalogItemSchema(
                value="STORE_PICKUP",
                label="Recojo en Tienda",
            ),
            CatalogItemSchema(value="PARCEL_SERVICE", label="Paquetería"),
        ]


class CommerceDeliveryPaidByProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(value="FREE", label="Sin Costo"),
            CatalogItemSchema(value="CUSTOMER", label="Cliente"),
            CatalogItemSchema(value="STORE", label="Tienda / Empresa"),
        ]


class CommercePaymentMethodsProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(value="QR", label="Pago QR"),
            CatalogItemSchema(value="CASH", label="Efectivo"),
            CatalogItemSchema(value="TRANSFER", label="Transferencia Bancaria"),
            CatalogItemSchema(value="COURTESY", label="Cortesía / Regalo (0 Bs)"),
        ]


class CommerceDeliveryStatusesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        return [
            CatalogItemSchema(value="DELIVERED", label="Entregado"),
            CatalogItemSchema(value="PENDING", label="Pendiente de Envío"),
            CatalogItemSchema(value="SHIPPED", label="Enviado por Flota"),
        ]


class CommerceProductMastersProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = (
            select(ProductMaster.id, ProductMaster.item_number, ProductMaster.name)
            .where(ProductMaster.is_active == True)  # noqa: E712
            .order_by(col(ProductMaster.item_number))
        )
        results = session.exec(query).all()
        return [
            CatalogItemSchema(value=r[0], label=f"#{r[1]} - {r[2]}") for r in results
        ]
