from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth import service as auth_service
from auth.middleware import get_current_user
from auth.models import User
from auth.schemas import UserResponse
from core.db import get_db

router = APIRouter()

VALID_PROVIDERS = {"google", "github"}


@router.get("/{provider}/login")
async def login(provider: str, response: Response) -> RedirectResponse:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")
    raw_state, signed_state = auth_service.generate_state()
    url = auth_service.get_authorization_url(provider, raw_state)
    redirect = RedirectResponse(url=url)
    redirect.set_cookie("oauth_state", signed_state, httponly=True, samesite="lax", max_age=600)
    return redirect


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str,
    state: str,
    response: Response,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Missing state cookie")
    try:
        user, token = await auth_service.handle_callback(db, provider, code, state, oauth_state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Sign-in failed")
    except Exception:
        raise HTTPException(status_code=400, detail="Sign-in failed")

    csrf_serializer = auth_service._get_serializer()
    csrf_token = csrf_serializer.dumps(token[:16])  # use partial token as CSRF basis

    redirect = RedirectResponse(url="/dashboard")
    redirect.set_cookie(
        "session", token, httponly=True, secure=True, samesite="lax",
        max_age=auth_service.settings.jwt_expiry_seconds,
    )
    redirect.set_cookie(
        "csrf_token", csrf_token, httponly=False, secure=True, samesite="lax",
        max_age=auth_service.settings.jwt_expiry_seconds,
    )
    redirect.delete_cookie("oauth_state")
    return redirect


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    response = Response()
    response.delete_cookie("session")
    response.delete_cookie("csrf_token")
    return {"message": "Logged out"}
