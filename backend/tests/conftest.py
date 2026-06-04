import uuid
from collections.abc import AsyncGenerator

import pytest
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
        email=email,
        display_name=display_name,
        provider="google",
        provider_id=str(uuid.uuid4()),
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

    from auth.middleware import get_current_user
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, user

    app.dependency_overrides.clear()
