import secrets
import time
from typing import Any

import httpx
import structlog
from itsdangerous import URLSafeTimedSerializer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from auth.repository import CognitoProfile, upsert_cognito_user
from core.config import settings
from groups.repository import link_pending_members

logger = structlog.get_logger()


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.csrf_secret_key.get_secret_value())


def generate_state() -> tuple[str, str]:
    """Returns (raw_state, signed_cookie_value)."""
    raw = secrets.token_urlsafe(32)
    signed = _get_serializer().dumps(raw)
    return raw, signed


def validate_state(raw_state: str, cookie_value: str) -> bool:
    try:
        stored = _get_serializer().loads(cookie_value, max_age=600)
        return secrets.compare_digest(stored, raw_state)
    except Exception:
        return False


def get_authorization_url(state: str) -> str:
    redirect_uri = f"{settings.app_base_url}/auth/callback"
    return (
        f"{settings.cognito_base_url}/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={settings.cognito_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid+email+profile"
        f"&state={state}"
    )


def get_logout_url() -> str:
    redirect_uri = f"{settings.app_base_url}/auth/logout-callback"
    return (
        f"{settings.cognito_base_url}/logout"
        f"?client_id={settings.cognito_client_id}"
        f"&logout_uri={redirect_uri}"
    )


async def _exchange_code(code: str) -> dict[str, Any]:
    redirect_uri = f"{settings.app_base_url}/auth/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.cognito_base_url}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.cognito_client_id,
            },
            auth=(
                settings.cognito_client_id,
                settings.cognito_client_secret.get_secret_value(),
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return dict(resp.json())


# Cache JWKS for 1 hour — avoid fetching on every request
_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 3600.0


async def _get_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at
    if not _jwks_cache or (time.monotonic() - _jwks_fetched_at) > _JWKS_TTL:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.cognito_jwks_url)
            resp.raise_for_status()
            _jwks_cache = dict(resp.json())
            _jwks_fetched_at = time.monotonic()
    return _jwks_cache


async def validate_token(id_token: str) -> dict[str, Any]:
    """Validate a Cognito ID token. Returns the decoded claims."""
    jwks = await _get_jwks()
    try:
        claims: dict[str, Any] = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=settings.cognito_issuer,
        )
    except JWTError as e:
        raise ValueError("Invalid token") from e
    if claims.get("token_use") != "id":
        raise ValueError("Not an ID token")
    return claims


def _extract_display_name(claims: dict[str, Any]) -> str:
    name = claims.get("name") or claims.get("cognito:username") or ""
    if not name:
        email: str = claims.get("email", "")
        name = email.split("@")[0]
    return str(name)


async def handle_callback(
    db: AsyncSession, code: str, state: str, state_cookie: str
) -> tuple[User, str]:
    if not validate_state(state, state_cookie):
        raise ValueError("Invalid OAuth2 state parameter")

    tokens = await _exchange_code(code)
    id_token: str = tokens["id_token"]
    claims = await validate_token(id_token)

    profile = CognitoProfile(
        cognito_sub=str(claims["sub"]),
        email=str(claims["email"]),
        display_name=_extract_display_name(claims),
        avatar_url=claims.get("picture"),
    )

    user, is_new = await upsert_cognito_user(db, profile)
    if is_new:
        await link_pending_members(db, user)
    await db.flush()

    logger.info("user_signed_in", user_id=str(user.id), sub=profile.cognito_sub, is_new=is_new)
    return user, id_token
