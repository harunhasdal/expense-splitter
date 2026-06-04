import secrets
from datetime import datetime, timezone

import httpx
import structlog
from itsdangerous import URLSafeTimedSerializer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from auth.repository import OAuthProfile, upsert_oauth_user
from core.config import settings
from groups.repository import link_pending_members

logger = structlog.get_logger()

PROVIDER_CONFIGS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": "read:user user:email",
    },
}


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


def get_authorization_url(provider: str, state: str) -> str:
    cfg = PROVIDER_CONFIGS[provider]
    client_id = (
        settings.google_client_id if provider == "google" else settings.github_client_id
    )
    redirect_uri = f"{settings.app_base_url}/auth/{provider}/callback"
    return (
        f"{cfg['auth_url']}?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope={cfg['scopes']}&state={state}"
    )


async def _exchange_code(provider: str, code: str) -> str:
    cfg = PROVIDER_CONFIGS[provider]
    client_id = settings.google_client_id if provider == "google" else settings.github_client_id
    client_secret = (
        settings.google_client_secret if provider == "google" else settings.github_client_secret
    ).get_secret_value()
    redirect_uri = f"{settings.app_base_url}/auth/{provider}/callback"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            cfg["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _fetch_profile(provider: str, access_token: str) -> OAuthProfile:
    cfg = PROVIDER_CONFIGS[provider]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    if provider == "google":
        return OAuthProfile(
            email=data["email"],
            display_name=data.get("name", data["email"]),
            avatar_url=data.get("picture"),
            provider="google",
            provider_id=data["sub"],
        )
    else:
        email = data.get("email") or f"{data['login']}@users.noreply.github.com"
        return OAuthProfile(
            email=email,
            display_name=data.get("name") or data["login"],
            avatar_url=data.get("avatar_url"),
            provider="github",
            provider_id=str(data["id"]),
        )


def issue_jwt(user: User) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": now,
        "exp": now + settings.jwt_expiry_seconds,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_issuer,
    }
    return jwt.encode(
        payload,
        settings.jwt_private_key.get_secret_value(),
        algorithm="RS256",
    )


async def handle_callback(
    db: AsyncSession, provider: str, code: str, state: str, state_cookie: str
) -> tuple[User, str]:
    if not validate_state(state, state_cookie):
        raise ValueError("Invalid OAuth2 state parameter")

    access_token = await _exchange_code(provider, code)
    profile = await _fetch_profile(provider, access_token)

    async with db.begin():
        user, is_new = await upsert_oauth_user(db, profile)
        if is_new:
            await link_pending_members(db, user)

    token = issue_jwt(user)
    logger.info("user_signed_in", user_id=str(user.id), provider=provider, is_new=is_new)
    return user, token


async def validate_token(token: str) -> dict[str, object]:
    try:
        return jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=["RS256"],
            audience=settings.jwt_issuer,
            issuer=settings.jwt_issuer,
        )
    except JWTError as e:
        raise ValueError("Invalid token") from e
