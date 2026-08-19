import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import repository as user_repo
from auth.models import User
from groups import repository as group_repo
from groups.models import Group, Member

logger = structlog.get_logger()


async def _load_group(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    """Load a group with its members eagerly (avoids MissingGreenlet outside async context)."""
    result = await db.execute(
        select(Group).where(Group.id == group_id).options(selectinload(Group.members))
    )
    return result.scalar_one_or_none()


async def _require_member(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> Member:
    member = await group_repo.get_active_member(db, group_id, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Group not found")
    return member


async def _require_owner(group: Group, user_id: uuid.UUID) -> None:
    if group.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Owner access required")


async def create_group(
    db: AsyncSession, owner: User, name: str, description: str | None
) -> Group:
    group = await group_repo.create(db, owner.id, name, description)
    await group_repo.add_member(db, group.id, owner)
    await db.flush()
    logger.info("group_created", group_id=str(group.id), owner_id=str(owner.id))
    loaded = await _load_group(db, group.id)
    assert loaded is not None
    return loaded


async def get_group(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> Group:
    await _require_member(db, group_id, user_id)
    group = await _load_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


async def list_groups(
    db: AsyncSession, user_id: uuid.UUID, include_archived: bool = False
) -> list[Group]:
    groups = await group_repo.list_for_user(db, user_id, include_archived)
    # Re-load each group with members eagerly to avoid MissingGreenlet on serialization
    loaded = []
    for g in groups:
        lg = await _load_group(db, g.id)
        if lg:
            loaded.append(lg)
    return loaded


async def archive_group(
    db: AsyncSession, group_id: uuid.UUID, user: User, force: bool = False
) -> Group:
    group = await group_repo.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await _require_owner(group, user.id)

    # Import here to avoid circular dependency
    from balance.service import get_raw_balances
    balances = await get_raw_balances(db, group_id)
    has_nonzero = any(
        abs(b) > Decimal("0.001")
        for balances_by_currency in balances.values()
        for b in balances_by_currency.values()
    )

    if has_nonzero and not force:
        raise HTTPException(status_code=409, detail="Group has unsettled balances")

    await group_repo.update_group(
        db, group,
        archived_at=datetime.now(UTC),
        archived_by=user.id,
        force_archived=has_nonzero and force,
    )
    await db.flush()

    if has_nonzero and force:
        logger.warning(
            "group_force_archived",
            group_id=str(group_id),
            actor_id=str(user.id),
            balances=str(balances),
        )
    loaded = await _load_group(db, group_id)
    assert loaded is not None
    return loaded


async def add_member(
    db: AsyncSession, group_id: uuid.UUID, requesting_user: User, email: str
) -> Member:
    group = await group_repo.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await _require_owner(group, requesting_user.id)

    if await group_repo.member_email_exists(db, group_id, email):
        raise HTTPException(status_code=409, detail="User is already a member of this group")

    target_user = await user_repo.get_by_email(db, email)
    if target_user:
        member = await group_repo.add_member(db, group_id, target_user)
    else:
        member = await group_repo.add_pending_member(db, group_id, email)
    await db.flush()

    logger.info("member_added", group_id=str(group_id), email=email)
    return member


async def remove_member(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID, requesting_user: User
) -> None:
    group = await group_repo.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await _require_owner(group, requesting_user.id)

    member = await group_repo.get_member_by_id(db, member_id)
    if not member or member.group_id != group_id or member.removed_at is not None:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.user_id == group.owner_id:
        raise HTTPException(status_code=409, detail="Cannot remove sole group owner")

    from balance.service import get_raw_balances
    balances = await get_raw_balances(db, group_id)
    member_has_balance = any(
        abs(balances_by_currency.get(member_id, Decimal(0))) > Decimal("0.001")
        for balances_by_currency in balances.values()
    )
    if member_has_balance:
        raise HTTPException(
            status_code=409,
            detail="Member has unsettled balance; settle before removing",
        )

    await group_repo.remove_member(db, member, requesting_user.id)
    await db.flush()

    logger.info("member_removed", group_id=str(group_id), member_id=str(member_id))
