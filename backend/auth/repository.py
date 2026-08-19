import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User

logger = structlog.get_logger()


@dataclass
class CognitoProfile:
    cognito_sub: str
    email: str
    display_name: str
    avatar_url: str | None


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def upsert_cognito_user(db: AsyncSession, profile: CognitoProfile) -> tuple[User, bool]:
    """Upsert by cognito_sub. Returns (user, is_new)."""
    now = datetime.now(UTC)
    email = profile.email.lower()

    result = await db.execute(select(User).where(User.cognito_sub == profile.cognito_sub))
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

    # New user — also check email to avoid duplicates if sub changes (rare edge case)
    existing = await get_by_email(db, email)
    if existing:
        await db.execute(
            update(User)
            .where(User.id == existing.id)
            .values(
                cognito_sub=profile.cognito_sub,
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                last_sign_in_at=now,
            )
        )
        await db.refresh(existing)
        return existing, False

    new_user = User(
        cognito_sub=profile.cognito_sub,
        email=email,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        created_at=now,
        last_sign_in_at=now,
    )
    db.add(new_user)
    await db.flush()
    return new_user, True
