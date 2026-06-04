import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from expenses.models import Expense, ExpenseSplit


@dataclass
class ExpenseRecord:
    expense_id: uuid.UUID
    payer_member_id: uuid.UUID
    currency: str
    splits: list[tuple[uuid.UUID, Decimal]]  # (member_id, computed_amount)


async def create(
    db: AsyncSession,
    group_id: uuid.UUID,
    payer_id: uuid.UUID,
    description: str,
    amount: Decimal,
    currency: str,
    expense_date: object,
    split_type: str,
    created_by: uuid.UUID,
    shares: list[tuple[uuid.UUID, Decimal | None, Decimal]],  # (member_id, raw_value, computed)
) -> Expense:
    expense = Expense(
        group_id=group_id,
        payer_id=payer_id,
        description=description,
        amount=float(amount),
        currency=currency,
        expense_date=expense_date,
        split_type=split_type,
        created_by=created_by,
    )
    db.add(expense)
    await db.flush()
    for member_id, raw_value, computed_amount in shares:
        split = ExpenseSplit(
            expense_id=expense.id,
            member_id=member_id,
            raw_value=float(raw_value) if raw_value is not None else None,
            computed_amount=float(computed_amount),
        )
        db.add(split)
    await db.flush()
    return expense


async def get_by_id(db: AsyncSession, expense_id: uuid.UUID) -> Expense | None:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    return result.scalar_one_or_none()


async def list_for_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    payer_id: uuid.UUID | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> tuple[list[Expense], int]:
    stmt = select(Expense).where(Expense.group_id == group_id)
    if not include_archived:
        stmt = stmt.where(Expense.archived_at.is_(None))
    if payer_id:
        stmt = stmt.where(Expense.payer_id == payer_id)
    stmt = stmt.order_by(Expense.expense_date.desc(), Expense.created_at.desc())

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def archive(
    db: AsyncSession, expense: Expense, archived_by: uuid.UUID
) -> Expense:
    expense.archived_at = datetime.now(timezone.utc)
    expense.archived_by = archived_by
    await db.flush()
    return expense


async def get_all_for_balance(db: AsyncSession, group_id: uuid.UUID) -> list[ExpenseRecord]:
    result = await db.execute(
        select(Expense).where(Expense.group_id == group_id, Expense.archived_at.is_(None))
    )
    records = []
    for expense in result.scalars().all():
        splits = [(s.member_id, Decimal(str(s.computed_amount))) for s in expense.splits]
        records.append(
            ExpenseRecord(
                expense_id=expense.id,
                payer_member_id=expense.payer_id,
                currency=expense.currency,
                splits=splits,
            )
        )
    return records
