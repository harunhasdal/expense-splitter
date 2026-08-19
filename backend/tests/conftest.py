import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth.models import User
from core.db import Base, get_db
from main import create_app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


def make_test_user(
    email: str = "test@example.com", display_name: str = "Test User"
) -> User:
    return User(
        id=uuid.uuid4(),
        cognito_sub=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
    )


@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    user = make_test_user()
    db_session.add(user)
    await db_session.commit()

    app = create_app()

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_current_user() -> User:
        return user

    from itsdangerous import URLSafeTimedSerializer

    from auth.middleware import get_current_user
    from core.config import settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user

    # Build a valid CSRF double-submit pair so all mutation requests pass CSRFMiddleware
    csrf_token = URLSafeTimedSerializer(settings.csrf_secret_key.get_secret_value()).dumps("test")

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
        cookies={"csrf_token": csrf_token},
        headers={"X-CSRF-Token": csrf_token},
    ) as client:
        yield client, user

    app.dependency_overrides.clear()
