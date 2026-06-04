import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User

logger = structlog.get_logger()


@dataclass
class OAuthProfile:
    email: str
    display_name: str
    avatar_url: str | None
    provider: str
    provider_id: str


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def upsert_oauth_user(db: AsyncSession, profile: OAuthProfile) -> tuple[User, bool]:
    """Returns (user, is_new). is_new=True when created for the first time."""
    now = datetime.now(timezone.utc)
    email = profile.email.lower()

    # Check by provider identity first
    result = await db.execute(
        select(User).where(User.provider == profile.provider, User.provider_id == profile.provider_id)
    )
    user = result.scalar_one_or_none()

    if user:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                last_sign_in_at=now,
            )
        )
        await db.refresh(user)
        return user, False

    # Check by email (different provider, same person)
    existing = await get_by_email(db, email)
    if existing:
        await db.execute(
            update(User)
            .where(User.id == existing.id)
            .values(
                provider=profile.provider,
                provider_id=profile.provider_id,
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                last_sign_in_at=now,
            )
        )
        await db.refresh(existing)
        return existing, False

    # New user
    new_user = User(
        email=email,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        provider=profile.provider,
        provider_id=profile.provider_id,
        created_at=now,
        last_sign_in_at=now,
    )
    db.add(new_user)
    await db.flush()
    return new_user, True
