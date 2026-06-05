from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth import service as auth_service
from auth.middleware import get_current_user
from auth.models import User
from auth.schemas import UserResponse
from core.config import settings
from core.db import get_db

router = APIRouter()


@router.get("/login")
async def login(response: Response) -> RedirectResponse:
    raw_state, signed_state = auth_service.generate_state()
    url = auth_service.get_authorization_url(raw_state)
    redirect = RedirectResponse(url=url)
    redirect.set_cookie("oauth_state", signed_state, httponly=True, samesite="lax", max_age=600)
    return redirect


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Missing state cookie")
    try:
        user, id_token = await auth_service.handle_callback(db, code, state, oauth_state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Sign-in failed")
    except Exception:
        raise HTTPException(status_code=400, detail="Sign-in failed")

    csrf_serializer = auth_service._get_serializer()
    csrf_token = csrf_serializer.dumps(id_token[:16])

    redirect = RedirectResponse(url="/dashboard")
    redirect.set_cookie(
        "session", id_token, httponly=True, secure=True, samesite="lax",
        max_age=settings.jwt_expiry_seconds,
    )
    redirect.set_cookie(
        "csrf_token", csrf_token, httponly=False, secure=True, samesite="lax",
        max_age=settings.jwt_expiry_seconds,
    )
    redirect.delete_cookie("oauth_state")
    return redirect


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> RedirectResponse:
    logout_url = auth_service.get_logout_url()
    redirect = RedirectResponse(url=logout_url)
    redirect.delete_cookie("session")
    redirect.delete_cookie("csrf_token")
    return redirect


@router.get("/logout-callback")
async def logout_callback() -> RedirectResponse:
    """Landing page after Cognito clears its session."""
    return RedirectResponse(url="/signin")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
