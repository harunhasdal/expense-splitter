import uuid

import structlog
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auth import repository as user_repo
from auth import service as auth_service
from auth.models import User
from core.db import get_db

logger = structlog.get_logger()


async def get_current_user(
    session_token: str | None = Cookie(default=None, alias="session"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        claims = await auth_service.validate_token(session_token)
        user_id_str = str(claims.get("custom:app_user_id", ""))
        # Fall back to lookup by cognito_sub when app_user_id claim is absent
        cognito_sub = str(claims["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Authentication required")

    user: User | None = None
    if user_id_str:
        try:
            user = await user_repo.get_by_id(db, uuid.UUID(user_id_str))
        except ValueError:
            pass

    if not user:
        from sqlalchemy import select
        from core.db import AsyncSessionLocal
        result = await db.execute(
            select(User).where(User.cognito_sub == cognito_sub)
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    structlog.contextvars.bind_contextvars(actor_id=str(user.id))
    return user
