"""
Shared test fixtures for the Reel48+ backend test suite.

Provides:
- A test database session using Alembic migrations (includes RLS policies)
- A non-superuser `reel48_app` role for RLS-enforced queries
- A superuser `admin_db_session` for seeding data that bypasses RLS
- Token generation with real JWT signing (monkeypatched JWKS)
- Multi-tenant fixtures: Company A + Company B (company-only tenancy)
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
from app.models.user import User
from app.services.cognito_service import CognitoService, get_cognito_service

# ---------------------------------------------------------------------------
# Test database URLs
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reel48_test",
)
TEST_DATABASE_URL_APP = os.getenv(
    "TEST_DATABASE_URL_APP",
    "postgresql+asyncpg://reel48_app:reel48_app@localhost:5432/reel48_test",
)


# ---------------------------------------------------------------------------
# Test RSA keypair for JWT signing
# ---------------------------------------------------------------------------
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_public_key = _test_private_key.public_key()
_test_kid = "test-key-1"

_test_private_key_pem = _test_private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()

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
    role: str = "employee",
) -> str:
    """Generate a real JWT signed with the test RSA key."""
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

    return jose_jwt.encode(
        claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
    )


# ---------------------------------------------------------------------------
# Database setup — Alembic migrations + reel48_app role
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def setup_database() -> AsyncGenerator[dict, None]:
    cleanup_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with cleanup_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await cleanup_engine.dispose()

    backend_dir = os.path.dirname(os.path.dirname(__file__))
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        check=True,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
    )

    engine_admin = create_async_engine(TEST_DATABASE_URL, echo=False)
    engine_app = create_async_engine(TEST_DATABASE_URL_APP, echo=False)
    admin_factory = async_sessionmaker(engine_admin, class_=AsyncSession, expire_on_commit=False)
    app_factory = async_sessionmaker(engine_app, class_=AsyncSession, expire_on_commit=False)

    async with engine_admin.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = 'reel48_app'")
        )
        if result.scalar() is None:
            await conn.execute(text("CREATE ROLE reel48_app WITH LOGIN PASSWORD 'reel48_app'"))

        # Grant permissions on the surviving tables only
        tables = [
            "companies",
            "users",
            "invites",
            "org_codes",
            "employee_profiles",
            "notifications",
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
    """Async HTTP test client using admin_db_session (bypasses RLS)."""

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
# Multi-tenant fixtures (company-only)
# ---------------------------------------------------------------------------
@pytest.fixture
async def company_a(admin_db_session: AsyncSession) -> Company:
    company = Company(name="Company A", slug="company-a", is_active=True)
    admin_db_session.add(company)
    await admin_db_session.flush()
    return company


@pytest.fixture
async def company_b(admin_db_session: AsyncSession) -> Company:
    company = Company(name="Company B", slug="company-b", is_active=True)
    admin_db_session.add(company)
    await admin_db_session.flush()
    return company


@pytest.fixture
async def reel48_company(admin_db_session: AsyncSession) -> Company:
    """Internal operator company that reel48_admin users belong to."""
    company = Company(name="Reel48 Operations", slug="reel48-ops", is_active=True)
    admin_db_session.add(company)
    await admin_db_session.flush()
    return company


# ---------------------------------------------------------------------------
# User fixtures (Company A)
# ---------------------------------------------------------------------------
@pytest.fixture
async def user_a_admin(admin_db_session: AsyncSession, company_a: Company) -> User:
    user = User(
        company_id=company_a.id,
        cognito_sub=str(uuid4()),
        email=f"admin-{uuid4().hex[:6]}@companya.com",
        full_name="Company A Admin",
        role="company_admin",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
async def user_a_manager(admin_db_session: AsyncSession, company_a: Company) -> User:
    user = User(
        company_id=company_a.id,
        cognito_sub=str(uuid4()),
        email=f"manager-{uuid4().hex[:6]}@companya.com",
        full_name="Company A Manager",
        role="manager",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
async def user_a_employee(admin_db_session: AsyncSession, company_a: Company) -> User:
    user = User(
        company_id=company_a.id,
        cognito_sub=str(uuid4()),
        email=f"employee-{uuid4().hex[:6]}@companya.com",
        full_name="Company A Employee",
        role="employee",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
async def user_b_employee(admin_db_session: AsyncSession, company_b: Company) -> User:
    user = User(
        company_id=company_b.id,
        cognito_sub=str(uuid4()),
        email=f"employee-{uuid4().hex[:6]}@companyb.com",
        full_name="Company B Employee",
        role="employee",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


@pytest.fixture
async def reel48_admin_user(
    admin_db_session: AsyncSession, reel48_company: Company
) -> User:
    user = User(
        company_id=reel48_company.id,
        cognito_sub=str(uuid4()),
        email=f"platform-admin-{uuid4().hex[:6]}@reel48.com",
        full_name="Platform Admin",
        role="reel48_admin",
    )
    admin_db_session.add(user)
    await admin_db_session.flush()
    return user


# ---------------------------------------------------------------------------
# Token fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def reel48_admin_token() -> str:
    """JWT for a reel48_admin (no company_id claim → RLS bypass)."""
    return create_test_token(role="reel48_admin")


@pytest.fixture
def reel48_admin_user_token(reel48_admin_user: User) -> str:
    """JWT matching the reel48_admin_user fixture's cognito_sub."""
    return create_test_token(
        user_id=reel48_admin_user.cognito_sub,
        role="reel48_admin",
    )


@pytest.fixture
def company_a_admin_token(company_a: Company) -> str:
    return create_test_token(company_id=str(company_a.id), role="company_admin")


@pytest.fixture
def company_a_manager_token(company_a: Company) -> str:
    return create_test_token(company_id=str(company_a.id), role="manager")


@pytest.fixture
def company_a_employee_token(company_a: Company) -> str:
    return create_test_token(company_id=str(company_a.id), role="employee")


@pytest.fixture
def company_b_employee_token(company_b: Company) -> str:
    return create_test_token(company_id=str(company_b.id), role="employee")


@pytest.fixture
def user_a_admin_token(user_a_admin: User, company_a: Company) -> str:
    """JWT matching user_a_admin's cognito_sub."""
    return create_test_token(
        user_id=user_a_admin.cognito_sub,
        company_id=str(company_a.id),
        role="company_admin",
    )


@pytest.fixture
def user_a_manager_token(user_a_manager: User, company_a: Company) -> str:
    return create_test_token(
        user_id=user_a_manager.cognito_sub,
        company_id=str(company_a.id),
        role="manager",
    )


@pytest.fixture
def user_a_employee_token(user_a_employee: User, company_a: Company) -> str:
    return create_test_token(
        user_id=user_a_employee.cognito_sub,
        company_id=str(company_a.id),
        role="employee",
    )


# ---------------------------------------------------------------------------
# Mock Cognito service
# ---------------------------------------------------------------------------
class MockCognitoService(CognitoService):
    """Mock Cognito service that returns predictable values without hitting AWS."""

    def __init__(self) -> None:
        self.created_users: list[dict] = []
        self.disabled_users: list[str] = []

    async def create_cognito_user(
        self, email, temporary_password, company_id, role
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
        self, email, password, company_id, role
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
    mock = MockCognitoService()
    app.dependency_overrides[get_cognito_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_cognito_service, None)


# ---------------------------------------------------------------------------
# Mock Email service
# ---------------------------------------------------------------------------
class MockEmailService:
    def __init__(self) -> None:
        self.sent_emails: list[dict] = []

    async def send_email(self, to_email, subject, html_body, text_body) -> str:
        message_id = f"mock-{len(self.sent_emails)}"
        self.sent_emails.append({
            "to_email": to_email,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "message_id": message_id,
        })
        return message_id


@pytest.fixture(autouse=True)
def mock_email() -> MockEmailService:
    from app.services.email_service import get_email_service

    mock = MockEmailService()
    app.dependency_overrides[get_email_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_email_service, None)


# ---------------------------------------------------------------------------
# Mock S3 service
# ---------------------------------------------------------------------------
class MockS3Service:
    def __init__(self) -> None:
        self.generated_upload_urls: list[dict] = []
        self.generated_download_urls: list[dict] = []

    def generate_upload_url(
        self, company_id, category, content_type, file_extension
    ) -> tuple[str, str]:
        from app.services.s3_service import _CATEGORY_RULES
        from app.core.exceptions import ValidationError as AppValidationError

        ext = file_extension.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"

        rules = _CATEGORY_RULES.get(category)
        if rules is None:
            raise AppValidationError(
                f"Invalid category '{category}'. Must be one of: {', '.join(_CATEGORY_RULES.keys())}"
            )

        if content_type not in rules["allowed_types"]:
            raise AppValidationError(
                f"Content type '{content_type}' is not allowed for category '{category}'. "
                f"Allowed: {', '.join(sorted(rules['allowed_types']))}"
            )

        if ext not in rules["allowed_extensions"]:
            raise AppValidationError(
                f"File extension '{ext}' is not allowed for category '{category}'. "
                f"Allowed: {', '.join(sorted(rules['allowed_extensions']))}"
            )

        s3_key = f"{company_id}/{category}/test-{uuid4()}{ext}"
        url = f"https://s3.amazonaws.com/reel48-assets/{s3_key}?presigned=true"
        self.generated_upload_urls.append({
            "company_id": str(company_id),
            "category": category,
            "content_type": content_type,
            "s3_key": s3_key,
        })
        return url, s3_key

    def generate_download_url(self, s3_key: str) -> str:
        url = f"https://s3.amazonaws.com/reel48-assets/{s3_key}?presigned=true"
        self.generated_download_urls.append({"s3_key": s3_key})
        return url


@pytest.fixture(autouse=True)
def mock_s3() -> MockS3Service:
    from app.services.s3_service import get_s3_service

    mock = MockS3Service()
    app.dependency_overrides[get_s3_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_s3_service, None)


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
async def org_code_a(
    admin_db_session: AsyncSession, company_a: Company, user_a_admin: User
) -> OrgCode:
    code = OrgCode(
        company_id=company_a.id,
        code="TESTA001",
        is_active=True,
        created_by=user_a_admin.id,
    )
    admin_db_session.add(code)
    await admin_db_session.flush()
    return code


@pytest.fixture
async def invite_a(
    admin_db_session: AsyncSession, company_a: Company, user_a_admin: User
) -> Invite:
    import secrets
    from datetime import timedelta

    now = datetime.now(UTC)
    invite = Invite(
        company_id=company_a.id,
        email="invited@companya.com",
        role="employee",
        token=secrets.token_hex(32),
        expires_at=now + timedelta(hours=72),
        created_by=user_a_admin.id,
    )
    admin_db_session.add(invite)
    await admin_db_session.flush()
    return invite
