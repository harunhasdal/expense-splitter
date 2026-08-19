import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settlements.models import Settlement


@dataclass
class SettlementRecord:
    settlement_id: uuid.UUID
    payer_member_id: uuid.UUID
    payee_member_id: uuid.UUID
    currency: str
    amount: Decimal


async def create(
    db: AsyncSession,
    group_id: uuid.UUID,
    payer_id: uuid.UUID,
    payee_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    recorded_by: uuid.UUID,
) -> Settlement:
    settlement = Settlement(
        group_id=group_id,
        payer_id=payer_id,
        payee_id=payee_id,
        amount=float(amount),
        currency=currency,
        recorded_by=recorded_by,
    )
    db.add(settlement)
    await db.flush()
    return settlement


async def list_for_group(db: AsyncSession, group_id: uuid.UUID) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.group_id == group_id)
        .order_by(Settlement.recorded_at.desc())
    )
    return list(result.scalars().all())


async def get_all_for_balance(db: AsyncSession, group_id: uuid.UUID) -> list[SettlementRecord]:
    result = await db.execute(select(Settlement).where(Settlement.group_id == group_id))
    return [
        SettlementRecord(
            settlement_id=s.id,
            payer_member_id=s.payer_id,
            payee_member_id=s.payee_id,
            currency=s.currency,
            amount=Decimal(str(s.amount)),
        )
        for s in result.scalars().all()
    ]
