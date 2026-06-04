import uuid

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from groups import repository as group_repo
from settlements import repository as settlement_repo
from settlements.models import Settlement
from settlements.schemas import SettlementCreate

logger = structlog.get_logger()


async def create_settlement(
    db: AsyncSession, group_id: uuid.UUID, user: User, payload: SettlementCreate
) -> Settlement:
    if not await group_repo.get_active_member(db, group_id, user.id):
        raise HTTPException(status_code=403, detail="Not a member of this group")

    payer = await group_repo.get_member_by_id(db, payload.payer_id)
    if not payer or payer.group_id != group_id or payer.removed_at is not None:
        raise HTTPException(status_code=400, detail="Payer must be an active group member")

    payee = await group_repo.get_member_by_id(db, payload.payee_id)
    if not payee or payee.group_id != group_id or payee.removed_at is not None:
        raise HTTPException(status_code=400, detail="Payee must be an active group member")

    async with db.begin():
        settlement = await settlement_repo.create(
            db,
            group_id=group_id,
            payer_id=payload.payer_id,
            payee_id=payload.payee_id,
            amount=payload.amount,
            currency=payload.currency,
            recorded_by=user.id,
        )

    logger.info("settlement_recorded", settlement_id=str(settlement.id), group_id=str(group_id))
    return settlement


async def list_settlements(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> list[Settlement]:
    if not await group_repo.get_active_member(db, group_id, user_id):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return await settlement_repo.list_for_group(db, group_id)
