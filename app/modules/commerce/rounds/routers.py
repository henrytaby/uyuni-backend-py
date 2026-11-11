from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.rounds.models import InvestmentRound
from app.modules.commerce.rounds.schemas import (
    InvestmentRoundCreate,
    InvestmentRoundRead,
    InvestmentRoundUpdate,
)
from app.modules.commerce.rounds.service import InvestmentRoundService

router = APIRouter(prefix="/rounds", tags=["Commerce - Investment Rounds"])


@router.post("/", response_model=InvestmentRoundRead)
def create_round(
    session: SessionDep,
    data: InvestmentRoundCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = InvestmentRoundService(session)
    return service.create(InvestmentRound(**data.model_dump()))


@router.get("/", response_model=list[InvestmentRoundRead])
def get_rounds(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = InvestmentRoundService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_rounds(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = InvestmentRoundService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=InvestmentRoundRead)
def get_round(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = InvestmentRoundService(session)
    round_obj = service.get_by_id(id)
    if not round_obj:
        raise NotFoundException(detail="Investment round not found")
    return round_obj


@router.put("/{id}", response_model=InvestmentRoundRead)
def update_round(
    id: UUID,
    data: InvestmentRoundUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = InvestmentRoundService(session)
    round_obj = service.update(id, data.model_dump(exclude_unset=True))
    if not round_obj:
        raise NotFoundException(detail="Investment round not found")
    return round_obj


@router.delete("/{id}")
def delete_round(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = InvestmentRoundService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Investment round not found")
    return {"message": "Investment round deleted successfully"}
