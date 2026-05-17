from uuid import UUID

from sqlmodel import Session, select

from app.core.catalogs.base import CatalogProvider
from app.core.catalogs.schemas import CatalogItemSchema
from app.modules.core.org_units.models import OrgUnit


class GerenciasProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        # Filtramos por parent_id IS NULL e is_active = True
        query = (
            select(OrgUnit.id, OrgUnit.name)
            .where(
                OrgUnit.parent_id == None,  # noqa: E711
                OrgUnit.is_active,
            )
            .order_by(OrgUnit.name)
        )

        results = session.exec(query).all()
        return [CatalogItemSchema(value=r[0], label=r[1]) for r in results]


class DepartamentosProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        gerencia_id_str = kwargs.get("gerencia_id")
        if not gerencia_id_str:
            return []

        # Validar si es un UUID válido antes de hacer el Query
        try:
            gerencia_id = UUID(gerencia_id_str)
        except ValueError:
            return []  # Retorna vacío si el UUID es inválido en vez de dar error 500

        query = (
            select(OrgUnit.id, OrgUnit.name)
            .where(OrgUnit.parent_id == gerencia_id, OrgUnit.is_active)
            .order_by(OrgUnit.name)
        )

        results = session.exec(query).all()
        return [CatalogItemSchema(value=r[0], label=r[1]) for r in results]
