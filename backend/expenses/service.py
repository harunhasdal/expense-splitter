import uuid
from datetime import date

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from expenses import repository as expense_repo
from expenses.models import Expense
from expenses.schemas import ExpenseCreate, ExpensePage, ExpenseResponse
from groups import repository as group_repo

logger = structlog.get_logger()


async def _validate_membership(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    member = await group_repo.get_active_member(db, group_id, user_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")


async def create_expense(
    db: AsyncSession, group_id: uuid.UUID, user: User, payload: ExpenseCreate
) -> Expense:
    await _validate_membership(db, group_id, user.id)

    # Validate date
    if payload.expense_date > date.today():
        raise HTTPException(status_code=400, detail="Expense date cannot be in the future")

    # Validate payer and split members are active
    payer = await group_repo.get_member_by_id(db, payload.payer_id)
    if not payer or payer.group_id != group_id or payer.removed_at is not None:
        raise HTTPException(status_code=400, detail="Payer must be an active group member")

    member_ids = [sd.member_id for sd in payload.split_details]
    for mid in member_ids:
        m = await group_repo.get_member_by_id(db, mid)
        if not m or m.group_id != group_id or m.removed_at is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Split member {mid} is not an active group member",
            )

    # Delegate to balance engine for validation and computation
    from balance.engine import SplitDetail as EngineSplitDetail
    from balance.engine import SplitType, compute_shares, validate_split
    engine_details = [
        EngineSplitDetail(member_id=sd.member_id, value=sd.value)
        for sd in payload.split_details
    ]
    validation = validate_split(
        SplitType(payload.split_type),
        payload.amount,
        member_ids,
        engine_details,
    )
    if not validation.valid:
        raise HTTPException(status_code=400, detail="; ".join(validation.errors))

    shares = compute_shares(
        SplitType(payload.split_type), payload.amount, member_ids, engine_details
    )

    share_tuples = [
        (s.member_id, s.raw_value, s.computed_amount) for s in shares
    ]

    expense = await expense_repo.create(
        db,
        group_id=group_id,
        payer_id=payload.payer_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        expense_date=payload.expense_date,
        split_type=payload.split_type,
        created_by=user.id,
        shares=share_tuples,
    )
    await db.flush()

    logger.info(
        "expense_created",
        expense_id=str(expense.id),
        group_id=str(group_id),
        actor=str(user.id),
    )
    return expense


async def list_expenses(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    payer_id: uuid.UUID | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> ExpensePage:
    await _validate_membership(db, group_id, user_id)
    expenses, total = await expense_repo.list_for_group(
        db, group_id, payer_id, include_archived, page, page_size
    )
    return ExpensePage(
        items=[ExpenseResponse.model_validate(e) for e in expenses],
        total=total,
        page=page,
        page_size=page_size,
    )


async def archive_expense(
    db: AsyncSession, group_id: uuid.UUID, expense_id: uuid.UUID, user: User
) -> Expense:
    # Check owner
    from sqlalchemy import select

    from groups.models import Group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Owner access required")

    expense = await expense_repo.get_by_id(db, expense_id)
    if not expense or expense.group_id != group_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.archived_at is not None:
        raise HTTPException(status_code=409, detail="Expense already archived")

    await expense_repo.archive(db, expense, user.id)
    await db.flush()

    logger.info(
        "expense_archived",
        expense_id=str(expense_id),
        group_id=str(group_id),
        actor=str(user.id),
        action="archived",
        resource_type="expense",
        resource_id=str(expense_id),
    )
    return expense
