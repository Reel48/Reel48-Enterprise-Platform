"""
Shared test fixtures for the Reel48+ backend test suite.

This conftest provides:
- A test database session with automatic rollback after each test
- Token generation helpers for different roles
- Multi-tenant test data fixtures (Company A with brands A1/A2, Company B with brand B1)
"""

import os
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db_session
from app.main import app
from app.models.base import Base

# Use a separate test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reel48_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
async def setup_database() -> AsyncGenerator[None, None]:
    """Create all tables at the start of the test session, drop at the end."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session(setup_database: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    async with test_async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with the test database session injected."""

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def create_test_token(
    user_id: str | None = None,
    company_id: str | None = None,
    sub_brand_id: str | None = None,
    role: str = "employee",
) -> str:
    """
    Generate a test JWT token with Reel48+ custom claims.

    In test mode, the auth middleware will accept these tokens without
    Cognito JWKS validation. This helper will be expanded in Phase 3
    when the auth middleware is implemented.
    """
    # Placeholder — will be implemented with proper JWT signing in Phase 3
    return f"test-token-{role}-{user_id or uuid4()}"
