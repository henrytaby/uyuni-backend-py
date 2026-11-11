from sqlmodel import Session, col, select

from app.core.catalogs.base import CatalogProvider
from app.core.catalogs.schemas import CatalogItemSchema
from app.models.role import Role


class CoreRolesProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        query = (
            select(Role.slug, Role.name, Role.icon, Role.description)
            .where(Role.is_active == True)  # noqa: E712
            .order_by(col(Role.sort_order))
        )
        results = session.exec(query).all()
        return [
            CatalogItemSchema(
                value=r[0],
                label=f"{r[2]} {r[1]}" if r[2] else r[1],
                extra={"description": r[3], "icon": r[2]} if r[3] or r[2] else None,
            )
            for r in results
        ]
