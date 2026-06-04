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
        payload = await auth_service.validate_token(session_token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Authentication required")

    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    structlog.contextvars.bind_contextvars(actor_id=str(user.id))
    return user
