"""
Shared test fixtures for the Reel48+ backend test suite.

This conftest provides:
- A test database session using Alembic migrations (includes RLS policies)
- A non-superuser `reel48_app` role for RLS-enforced queries
- A superuser `admin_db_session` for seeding data that bypasses RLS
- Token generation with real JWT signing (monkeypatched JWKS)
- Multi-tenant fixtures: Company A (brands A1, A2), Company B (brand B1)
"""

import base64
import os
import subprocess
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.dependencies import get_db_session
from app.core.rate_limit import rate_limit_auth
from app.main import app
from app.models.base import Base
from app.models.company import Company
from app.models.invite import Invite
from app.models.org_code import OrgCode
from app.models.sub_brand import SubBrand
from app.models.user import User
from app.services.cognito_service import CognitoService, get_cognito_service

# ---------------------------------------------------------------------------
# Test database URLs
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reel48_test",
)

# Non-superuser URL for RLS-enforced sessions
TEST_DATABASE_URL_APP = os.getenv(
    "TEST_DATABASE_URL_APP",
    "postgresql+asyncpg://reel48_app:reel48_app@localhost:5432/reel48_test",
)

# Engine and session factories are created lazily inside fixtures so they bind
# to pytest-asyncio's event loop, avoiding "Future attached to a different loop"
# errors that occur when engines are created at module import time.


# ---------------------------------------------------------------------------
# Test RSA keypair for JWT signing
# ---------------------------------------------------------------------------
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_public_key = _test_private_key.public_key()
_test_kid = "test-key-1"

# PEM for python-jose signing
_test_private_key_pem = _test_private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()

# Build JWK for the mock JWKS response
_pub_numbers = _test_public_key.public_numbers()


def _int_to_b64url(n: int) -> str:
    byte_length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(byte_length, "big")).rstrip(b"=").decode()


_test_jwk = {
    "kty": "RSA",
    "kid": _test_kid,
    "use": "sig",
    "alg": "RS256",
    "n": _int_to_b64url(_pub_numbers.n),
    "e": _int_to_b64url(_pub_numbers.e),
}


# ---------------------------------------------------------------------------
# Monkeypatch JWKS fetching (session-scoped, autouse)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _patch_jwks():
    """Replace _fetch_jwks so validate_cognito_token uses our test RSA key."""
    import app.core.security as security_module

    _original_fetch = security_module._fetch_jwks

    async def _mock_fetch_jwks() -> list[dict]:
        return [_test_jwk]

    security_module._fetch_jwks = _mock_fetch_jwks  # type: ignore[assignment]
    # Reset the cache so the patched function gets called
    security_module._jwks_keys = None
    security_module._jwks_fetched_at = 0.0

    yield

    security_module._fetch_jwks = _original_fetch  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Token helper
# ---------------------------------------------------------------------------
def create_test_token(
    user_id: str | None = None,
    company_id: str | None = None,
    sub_brand_id: str | None = None,
    role: str = "employee",
) -> str:
    """
    Generate a real JWT signed with the test RSA key.

    The full validate_cognito_token path runs against this token,
    verifying signature, exp, aud, iss — only the JWKS fetch is mocked.
    """
    now = int(time.time())
    claims: dict = {
        "sub": user_id or str(uuid4()),
        "iss": settings.cognito_issuer,
        "aud": settings.COGNITO_CLIENT_ID,
        "iat": now,
        "exp": now + 3600,
        "token_use": "id",
        "custom:role": role,
    }
    if company_id is not None:
        claims["custom:company_id"] = company_id
    if sub_brand_id is not None:
        claims["custom:sub_brand_id"] = sub_brand_id

    return jose_jwt.encode(
        claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
    )


# ---------------------------------------------------------------------------
# Database setup — Alembic migrations + reel48_app role
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def setup_database() -> AsyncGenerator[dict, None]:
    """
    Run Alembic migrations (creates tables + RLS policies), set up the
    non-superuser reel48_app role, and yield engine/session factories
    created inside pytest-asyncio's event loop.
    """
    # Clean up any leftover state from previous test runs (e.g., alembic_version
    # table persisting after Base.metadata.drop_all in teardown).
    cleanup_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with cleanup_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await cleanup_engine.dispose()

    # Run Alembic migrations via subprocess (avoids asyncio.run() conflict
    # with pytest-asyncio's event loop — env.py uses asyncio.run() internally).
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        check=True,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
    )

    # Create engines inside the fixture so they bind to pytest-asyncio's event loop
    engine_admin = create_async_engine(TEST_DATABASE_URL, echo=False)
    engine_app = create_async_engine(TEST_DATABASE_URL_APP, echo=False)
    admin_factory = async_sessionmaker(engine_admin, class_=AsyncSession, expire_on_commit=False)
    app_factory = async_sessionmaker(engine_app, class_=AsyncSession, expire_on_commit=False)

    # Create the non-superuser role for RLS testing
    async with engine_admin.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = 'reel48_app'")
        )
        if result.scalar() is None:
            await conn.execute(text("CREATE ROLE reel48_app WITH LOGIN PASSWORD 'reel48_app'"))

        # Grant permissions on all module tables
        tables = [
            "companies", "sub_brands", "users", "invites",
            "org_codes", "employee_profiles",
            "products", "catalogs", "catalog_products",
            "orders", "order_line_items",
        ]
        for table in tables:
            await conn.execute(
                text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO reel48_app")  # noqa: S608
            )

    yield {
        "engine_admin": engine_admin,
        "engine_app": engine_app,
        "admin_factory": admin_factory,
        "app_factory": app_factory,
    }

    # Teardown: drop all tables including alembic_version
    async with engine_admin.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await engine_admin.dispose()
    await engine_app.dispose()


# ---------------------------------------------------------------------------
# Database sessions
# ---------------------------------------------------------------------------
@pytest.fixture
async def admin_db_session(setup_database: dict) -> AsyncGenerator[AsyncSession, None]:
    """Superuser session for seeding data (bypasses RLS)."""
    async with setup_database["admin_factory"]() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
async def db_session(setup_database: dict) -> AsyncGenerator[AsyncSession, None]:
    """Non-superuser session (RLS enforced). Use for verifying isolation."""
    async with setup_database["app_factory"]() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
async def client(
    setup_database: None, admin_db_session: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client.

    Uses the admin_db_session (superuser) for the app's get_db_session override,
    so route handlers can insert/query data without RLS interference during
    functional tests. Isolation tests use db_session (reel48_app) directly.
    """

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield admin_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Multi-tenant fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def company_a(admin_db_session: AsyncSession):
    """Company A with two sub-brands (A1 default, A2)."""
    company = Company(name="Company A", slug="company-a", is_active=True)
    admin_db_session.add(company)
    await admin_db_session.flush()

    brand_a1 = SubBrand(
        company_id=company.id, name="Brand A1", slug="brand-a1", is_default=True, is_active=True
    )
    brand_a2 = SubBrand(
        company_id=company.id, name="Brand A2", slug="brand-a2", is_default=False, is_active=True
    )
    admin_db_session.add_all([brand_a1, brand_a2])
    await admin_db_session.flush()

    return company, brand_a1, brand_a2


@pytest.fixture
async def company_b(admin_db_session: AsyncSession):
    """Company B with one sub-brand (B1 default)."""
    company = Company(name="Company B", slug="company-b", is_active=True)
    admin_db_session.add(company)
    await admin_db_session.flush()

    brand_b1 = SubBrand(
        company_id=company.id, name="Brand B1", slug="brand-b1", is_default=True, is_active=True
    )
    admin_db_session.add(brand_b1)
    await admin_db_session.flush()

    return company, brand_b1


@pytest.fixture
async def user_a1_employee(admin_db_session: AsyncSession, company_a):
    """An employee user in Company A, Brand A1."""
    company, brand_a1, _brand_a2 = company_a
    user = User(
        company_id=company.id,
        sub_brand_id=brand_a1.id,
        cognito_sub=str(uuid4()),
        email=f"employee-a1-{uuid4().hex[:6]}@companya.com",
        full_name="Employee A1",
        role="employee",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
async def user_b1_employee(admin_db_session: AsyncSession, company_b):
    """An employee user in Company B, Brand B1."""
    company, brand_b1 = company_b
    user = User(
        company_id=company.id,
        sub_brand_id=brand_b1.id,
        cognito_sub=str(uuid4()),
        email=f"employee-b1-{uuid4().hex[:6]}@companyb.com",
        full_name="Employee B1",
        role="employee",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


# ---------------------------------------------------------------------------
# Token fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def reel48_admin_token() -> str:
    """JWT for a reel48_admin (platform operator, no company/sub-brand)."""
    return create_test_token(role="reel48_admin")


@pytest.fixture
def company_a_corporate_admin_token(company_a) -> str:
    """JWT for Company A's corporate admin (sub_brand_id=None)."""
    company, _a1, _a2 = company_a
    return create_test_token(company_id=str(company.id), role="corporate_admin")


@pytest.fixture
def company_a_brand_a1_admin_token(company_a) -> str:
    """JWT for Company A, Brand A1 sub-brand admin."""
    company, brand_a1, _a2 = company_a
    return create_test_token(
        company_id=str(company.id), sub_brand_id=str(brand_a1.id), role="sub_brand_admin"
    )


@pytest.fixture
def company_a_brand_a1_employee_token(company_a) -> str:
    """JWT for Company A, Brand A1 employee."""
    company, brand_a1, _a2 = company_a
    return create_test_token(
        company_id=str(company.id), sub_brand_id=str(brand_a1.id), role="employee"
    )


@pytest.fixture
def company_a_brand_a2_employee_token(company_a) -> str:
    """JWT for Company A, Brand A2 employee."""
    company, _a1, brand_a2 = company_a
    return create_test_token(
        company_id=str(company.id), sub_brand_id=str(brand_a2.id), role="employee"
    )


@pytest.fixture
def company_b_employee_token(company_b) -> str:
    """JWT for Company B, Brand B1 employee."""
    company, brand_b1 = company_b
    return create_test_token(
        company_id=str(company.id), sub_brand_id=str(brand_b1.id), role="employee"
    )


@pytest.fixture
def company_a_brand_a2_admin_token(company_a) -> str:
    """JWT for Company A, Brand A2 sub-brand admin."""
    company, _a1, brand_a2 = company_a
    return create_test_token(
        company_id=str(company.id), sub_brand_id=str(brand_a2.id), role="sub_brand_admin"
    )


@pytest.fixture
def company_b_corporate_admin_token(company_b) -> str:
    """JWT for Company B's corporate admin (sub_brand_id=None)."""
    company, _b1 = company_b
    return create_test_token(company_id=str(company.id), role="corporate_admin")


@pytest.fixture
def company_a_brand_a1_manager_token(company_a) -> str:
    """JWT for Company A, Brand A1 regional manager."""
    company, brand_a1, _a2 = company_a
    return create_test_token(
        company_id=str(company.id), sub_brand_id=str(brand_a1.id), role="regional_manager"
    )


@pytest.fixture
async def reel48_company(admin_db_session: AsyncSession):
    """Internal 'Reel48 Operations' company for platform admin users."""
    company = Company(name="Reel48 Operations", slug="reel48-ops", is_active=True)
    admin_db_session.add(company)
    await admin_db_session.flush()
    brand = SubBrand(
        company_id=company.id, name="Platform", slug="platform", is_default=True, is_active=True
    )
    admin_db_session.add(brand)
    await admin_db_session.flush()
    return company, brand


@pytest.fixture
async def reel48_admin_user(admin_db_session: AsyncSession, reel48_company):
    """A reel48_admin user with a real User record (for resolve_current_user_id)."""
    company, brand = reel48_company
    user = User(
        company_id=company.id,
        sub_brand_id=brand.id,
        cognito_sub=str(uuid4()),
        email=f"platform-admin-{uuid4().hex[:6]}@reel48.com",
        full_name="Platform Admin",
        role="reel48_admin",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
def reel48_admin_user_token(reel48_admin_user) -> str:
    """JWT for the reel48_admin_user fixture (cognito_sub matches, no company_id in JWT)."""
    return create_test_token(
        user_id=reel48_admin_user.cognito_sub,
        role="reel48_admin",
    )


@pytest.fixture
async def user_a1_admin(admin_db_session: AsyncSession, company_a):
    """A sub_brand_admin user in Company A, Brand A1."""
    company, brand_a1, _brand_a2 = company_a
    user = User(
        company_id=company.id,
        sub_brand_id=brand_a1.id,
        cognito_sub=str(uuid4()),
        email=f"admin-a1-{uuid4().hex[:6]}@companya.com",
        full_name="Admin A1",
        role="sub_brand_admin",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
async def user_a_corporate_admin(admin_db_session: AsyncSession, company_a):
    """A corporate_admin user in Company A (sub_brand_id=None)."""
    company, _a1, _a2 = company_a
    user = User(
        company_id=company.id,
        sub_brand_id=None,
        cognito_sub=str(uuid4()),
        email=f"corp-admin-{uuid4().hex[:6]}@companya.com",
        full_name="Corporate Admin A",
        role="corporate_admin",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
def user_a1_admin_token(user_a1_admin, company_a) -> str:
    """JWT for the user_a1_admin fixture (cognito_sub matches the User record)."""
    company, brand_a1, _a2 = company_a
    return create_test_token(
        user_id=user_a1_admin.cognito_sub,
        company_id=str(company.id),
        sub_brand_id=str(brand_a1.id),
        role="sub_brand_admin",
    )


@pytest.fixture
def user_a_corporate_admin_token(user_a_corporate_admin, company_a) -> str:
    """JWT for the user_a_corporate_admin fixture (cognito_sub matches)."""
    company, _a1, _a2 = company_a
    return create_test_token(
        user_id=user_a_corporate_admin.cognito_sub,
        company_id=str(company.id),
        role="corporate_admin",
    )


@pytest.fixture
def user_a1_employee_token(user_a1_employee, company_a) -> str:
    """JWT for the user_a1_employee fixture (cognito_sub matches the User record)."""
    company, brand_a1, _a2 = company_a
    return create_test_token(
        user_id=user_a1_employee.cognito_sub,
        company_id=str(company.id),
        sub_brand_id=str(brand_a1.id),
        role="employee",
    )


# ---------------------------------------------------------------------------
# Mock Cognito service
# ---------------------------------------------------------------------------
class MockCognitoService(CognitoService):
    """Mock Cognito service that returns predictable values without hitting AWS."""

    def __init__(self) -> None:
        # Don't call super().__init__ — no real client needed
        self.created_users: list[dict] = []
        self.disabled_users: list[str] = []

    async def create_cognito_user(
        self, email, temporary_password, company_id, sub_brand_id, role
    ) -> str:
        cognito_sub = str(uuid4())
        self.created_users.append({
            "cognito_sub": cognito_sub,
            "email": email,
            "role": role,
            "method": "admin_create",
        })
        return cognito_sub

    async def create_cognito_user_with_password(
        self, email, password, company_id, sub_brand_id, role
    ) -> str:
        cognito_sub = str(uuid4())
        self.created_users.append({
            "cognito_sub": cognito_sub,
            "email": email,
            "role": role,
            "method": "with_password",
        })
        return cognito_sub

    async def get_cognito_user(self, cognito_sub) -> dict | None:
        return None

    async def update_cognito_attributes(self, cognito_sub, attributes) -> None:
        pass

    async def disable_cognito_user(self, cognito_sub) -> None:
        self.disabled_users.append(cognito_sub)


@pytest.fixture(autouse=True)
def mock_cognito() -> MockCognitoService:
    """Auto-mock CognitoService for all tests. Override get_cognito_service."""
    mock = MockCognitoService()
    app.dependency_overrides[get_cognito_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_cognito_service, None)


@pytest.fixture(autouse=True)
def no_rate_limit():
    """Disable rate limiting for all tests by default."""

    async def _noop() -> None:
        return None

    app.dependency_overrides[rate_limit_auth] = _noop
    yield
    app.dependency_overrides.pop(rate_limit_auth, None)


# ---------------------------------------------------------------------------
# Registration fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def org_code_a(admin_db_session: AsyncSession, company_a, user_a_corporate_admin):
    """An active org code for Company A."""
    company, _a1, _a2 = company_a
    code = OrgCode(
        company_id=company.id,
        code="TESTA001",
        is_active=True,
        created_by=user_a_corporate_admin.id,
    )
    admin_db_session.add(code)
    await admin_db_session.flush()
    return code


@pytest.fixture
async def invite_a1(admin_db_session: AsyncSession, company_a, user_a_corporate_admin):
    """A valid (unconsumed, not expired) invite for Company A, Brand A1."""
    import secrets
    from datetime import timedelta

    company, brand_a1, _a2 = company_a
    now = datetime.now(UTC)
    invite = Invite(
        company_id=company.id,
        target_sub_brand_id=brand_a1.id,
        email="invited@companya.com",
        role="employee",
        token=secrets.token_hex(32),
        expires_at=now + timedelta(hours=72),
        created_by=user_a_corporate_admin.id,
    )
    admin_db_session.add(invite)
    await admin_db_session.flush()
    return invite
