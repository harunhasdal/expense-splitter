import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.models import User
from core.db import get_db
from settlements import service as settlement_service
from settlements.schemas import SettlementCreate, SettlementResponse

router = APIRouter()


@router.post("/{group_id}/settlements", response_model=SettlementResponse, status_code=201)
async def create_settlement(
    group_id: uuid.UUID,
    body: SettlementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettlementResponse:
    settlement = await settlement_service.create_settlement(db, group_id, current_user, body)
    return SettlementResponse.model_validate(settlement)


@router.get("/{group_id}/settlements", response_model=list[SettlementResponse])
async def list_settlements(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SettlementResponse]:
    settlements = await settlement_service.list_settlements(db, group_id, current_user.id)
    return [SettlementResponse.model_validate(s) for s in settlements]
