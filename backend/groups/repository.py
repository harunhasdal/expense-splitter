import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from groups.models import Group, Member


async def create(db: AsyncSession, owner_id: uuid.UUID, name: str, description: str | None) -> Group:
    group = Group(name=name, description=description, owner_id=owner_id)
    db.add(group)
    await db.flush()
    return group


async def get_by_id(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


async def list_for_user(
    db: AsyncSession, user_id: uuid.UUID, include_archived: bool = False
) -> list[Group]:
    stmt = (
        select(Group)
        .join(Member, Member.group_id == Group.id)
        .where(Member.user_id == user_id, Member.removed_at.is_(None))
    )
    if not include_archived:
        stmt = stmt.where(Group.archived_at.is_(None))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_group(db: AsyncSession, group: Group, **kwargs: object) -> Group:
    for key, value in kwargs.items():
        setattr(group, key, value)
    await db.flush()
    return group


async def add_member(
    db: AsyncSession, group_id: uuid.UUID, user: User
) -> Member:
    member = Member(
        group_id=group_id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_pending=False,
    )
    db.add(member)
    await db.flush()
    return member


async def add_pending_member(
    db: AsyncSession, group_id: uuid.UUID, email: str
) -> Member:
    local = email.split("@")[0]
    member = Member(
        group_id=group_id,
        user_id=None,
        email=email.lower(),
        display_name=local,
        is_pending=True,
    )
    db.add(member)
    await db.flush()
    return member


async def get_member_by_id(db: AsyncSession, member_id: uuid.UUID) -> Member | None:
    result = await db.execute(select(Member).where(Member.id == member_id))
    return result.scalar_one_or_none()


async def get_active_member(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Member | None:
    result = await db.execute(
        select(Member).where(
            Member.group_id == group_id,
            Member.user_id == user_id,
            Member.removed_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def member_email_exists(db: AsyncSession, group_id: uuid.UUID, email: str) -> bool:
    result = await db.execute(
        select(Member).where(
            Member.group_id == group_id,
            Member.email == email.lower(),
            Member.removed_at.is_(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def remove_member(
    db: AsyncSession, member: Member, removed_by: uuid.UUID
) -> Member:
    member.removed_at = datetime.now(timezone.utc)
    member.removed_by = removed_by
    member.display_name = "Former Member"
    await db.flush()
    return member


async def link_pending_members(db: AsyncSession, user: User) -> None:
    """Link all pending member entries for a newly registered user's email."""
    result = await db.execute(
        select(Member).where(Member.email == user.email, Member.is_pending.is_(True))
    )
    for member in result.scalars().all():
        member.user_id = user.id
        member.is_pending = False
        member.display_name = user.display_name
    await db.flush()
