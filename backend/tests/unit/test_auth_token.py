"""Regression tests for Cognito ID token validation (auth.service.validate_token).

Cognito ID tokens include an ``at_hash`` claim. python-jose tries to verify it
against the access token, which validate_token intentionally does not pass — so
without ``verify_at_hash: False`` a perfectly valid ID token is rejected with a
JWTClaimsError. These tests lock that behavior in.
"""

import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk as jose_jwk
from jose import jwt

from auth import service
from core.config import settings


def _make_keypair() -> tuple[str, dict[str, str]]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    public_jwk = jose_jwk.construct(pub_pem, "RS256").to_dict()
    public_jwk["kid"] = "test-kid"
    public_jwk["alg"] = "RS256"
    return priv_pem, public_jwk


def _mint_id_token(priv_pem: str, **overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": "cognito-sub-123",
        "email": "alice@example.com",
        "aud": settings.cognito_client_id,
        "iss": settings.cognito_issuer,
        "token_use": "id",
        "at_hash": "irrelevant-hash-value",  # present on every Cognito ID token
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return str(jwt.encode(claims, priv_pem, algorithm="RS256", headers={"kid": "test-kid"}))


async def test_validate_token_accepts_token_with_at_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    priv_pem, public_jwk = _make_keypair()

    async def fake_jwks() -> dict[str, object]:
        return {"keys": [public_jwk]}

    monkeypatch.setattr(service, "_get_jwks", fake_jwks)

    claims = await service.validate_token(_mint_id_token(priv_pem))

    assert claims["sub"] == "cognito-sub-123"
    assert claims["email"] == "alice@example.com"


async def test_validate_token_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    priv_pem, public_jwk = _make_keypair()

    async def fake_jwks() -> dict[str, object]:
        return {"keys": [public_jwk]}

    monkeypatch.setattr(service, "_get_jwks", fake_jwks)

    with pytest.raises(ValueError, match="Invalid token"):
        await service.validate_token(_mint_id_token(priv_pem, aud="some-other-client"))


async def test_validate_token_rejects_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """token_use must be 'id' — an access token should be refused."""
    priv_pem, public_jwk = _make_keypair()

    async def fake_jwks() -> dict[str, object]:
        return {"keys": [public_jwk]}

    monkeypatch.setattr(service, "_get_jwks", fake_jwks)

    with pytest.raises(ValueError, match="Not an ID token"):
        await service.validate_token(_mint_id_token(priv_pem, token_use="access"))  # noqa: S106
