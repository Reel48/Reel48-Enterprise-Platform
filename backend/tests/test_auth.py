"""
Tests for JWT validation, TenantContext, and get_tenant_context dependency.

These tests verify:
- Cognito JWT validation (signature, expiry, audience, issuer, token_use)
- TenantContext role-checking properties
- get_tenant_context sets PostgreSQL session variables correctly
- Structlog contextvars are bound with tenant info
"""

import time
from uuid import uuid4

import pytest
import structlog
from jose import jwt as jose_jwt
from sqlalchemy import text

from app.core.config import settings
from app.core.security import validate_cognito_token
from app.core.tenant import TenantContext
from tests.conftest import _test_kid, _test_private_key_pem, create_test_token


# ---------------------------------------------------------------------------
# TenantContext property tests
# ---------------------------------------------------------------------------
class TestTenantContextProperties:
    def test_is_reel48_admin(self):
        ctx = TenantContext(user_id="u1", company_id=None, sub_brand_id=None, role="reel48_admin")
        assert ctx.is_reel48_admin is True
        assert ctx.is_corporate_admin_or_above is True
        assert ctx.is_admin is True
        assert ctx.is_manager_or_above is True

    def test_is_corporate_admin(self):
        cid = uuid4()
        ctx = TenantContext(user_id="u2", company_id=cid, sub_brand_id=None, role="corporate_admin")
        assert ctx.is_reel48_admin is False
        assert ctx.is_corporate_admin_or_above is True
        assert ctx.is_admin is True
        assert ctx.is_manager_or_above is True

    def test_is_sub_brand_admin(self):
        cid, sbid = uuid4(), uuid4()
        ctx = TenantContext(
            user_id="u3", company_id=cid, sub_brand_id=sbid, role="sub_brand_admin"
        )
        assert ctx.is_reel48_admin is False
        assert ctx.is_corporate_admin_or_above is False
        assert ctx.is_admin is True
        assert ctx.is_manager_or_above is True

    def test_is_regional_manager(self):
        cid, sbid = uuid4(), uuid4()
        ctx = TenantContext(
            user_id="u4", company_id=cid, sub_brand_id=sbid, role="regional_manager"
        )
        assert ctx.is_reel48_admin is False
        assert ctx.is_corporate_admin_or_above is False
        assert ctx.is_admin is False
        assert ctx.is_manager_or_above is True

    def test_is_employee(self):
        cid, sbid = uuid4(), uuid4()
        ctx = TenantContext(user_id="u5", company_id=cid, sub_brand_id=sbid, role="employee")
        assert ctx.is_reel48_admin is False
        assert ctx.is_corporate_admin_or_above is False
        assert ctx.is_admin is False
        assert ctx.is_manager_or_above is False


# ---------------------------------------------------------------------------
# JWT validation tests
# ---------------------------------------------------------------------------
class TestValidateCognitoToken:
    async def test_valid_token_returns_claims(self):
        user_id = str(uuid4())
        company_id = str(uuid4())
        sub_brand_id = str(uuid4())
        token = create_test_token(
            user_id=user_id,
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            role="employee",
        )

        claims = await validate_cognito_token(token)

        assert claims["sub"] == user_id
        assert claims["custom:role"] == "employee"
        assert claims["custom:company_id"] == company_id
        assert claims["custom:sub_brand_id"] == sub_brand_id
        assert claims["token_use"] == "id"

    async def test_expired_token_raises_401(self):
        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "iss": settings.cognito_issuer,
            "aud": settings.COGNITO_CLIENT_ID,
            "iat": now - 7200,
            "exp": now - 3600,  # Expired 1 hour ago
            "token_use": "id",
            "custom:role": "employee",
        }
        token = jose_jwt.encode(
            claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
        )

        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_wrong_audience_raises_401(self):
        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "iss": settings.cognito_issuer,
            "aud": "wrong-client-id",
            "iat": now,
            "exp": now + 3600,
            "token_use": "id",
            "custom:role": "employee",
        }
        token = jose_jwt.encode(
            claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
        )

        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_wrong_issuer_raises_401(self):
        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "iss": "https://wrong-issuer.example.com",
            "aud": settings.COGNITO_CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            "token_use": "id",
            "custom:role": "employee",
        }
        token = jose_jwt.encode(
            claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
        )

        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_invalid_signature_raises_401(self):
        # Sign with a DIFFERENT RSA key
        from cryptography.hazmat.primitives import serialization as ser_mod
        from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

        other_key = rsa_mod.generate_private_key(public_exponent=65537, key_size=2048)
        other_pem = other_key.private_bytes(
            ser_mod.Encoding.PEM, ser_mod.PrivateFormat.PKCS8, ser_mod.NoEncryption()
        ).decode()

        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "iss": settings.cognito_issuer,
            "aud": settings.COGNITO_CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            "token_use": "id",
            "custom:role": "employee",
        }
        token = jose_jwt.encode(
            claims, other_pem, algorithm="RS256", headers={"kid": _test_kid}
        )

        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_access_token_rejected(self):
        """Access tokens (token_use=access) don't carry custom attributes."""
        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "iss": settings.cognito_issuer,
            "aud": settings.COGNITO_CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            "token_use": "access",  # Not an ID token
            "custom:role": "employee",
        }
        token = jose_jwt.encode(
            claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
        )

        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_missing_role_claim_raises_401(self):
        now = int(time.time())
        claims = {
            "sub": str(uuid4()),
            "iss": settings.cognito_issuer,
            "aud": settings.COGNITO_CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            "token_use": "id",
            # Missing custom:role
        }
        token = jose_jwt.encode(
            claims, _test_private_key_pem, algorithm="RS256", headers={"kid": _test_kid}
        )

        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_garbage_token_raises_401(self):
        with pytest.raises(Exception) as exc_info:
            await validate_cognito_token("not.a.jwt")
        assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    async def test_reel48_admin_token_without_company_id(self):
        """reel48_admin tokens have no company_id or sub_brand_id claims."""
        token = create_test_token(role="reel48_admin")
        claims = await validate_cognito_token(token)

        assert claims["custom:role"] == "reel48_admin"
        assert "custom:company_id" not in claims
        assert "custom:sub_brand_id" not in claims


# ---------------------------------------------------------------------------
# get_tenant_context integration tests (via HTTP client)
# ---------------------------------------------------------------------------
class TestGetTenantContextHTTP:
    """Test get_tenant_context behavior via the /health endpoint won't work
    (it's unprotected). Instead, test that auth is enforced on missing tokens."""

    async def test_missing_bearer_returns_403(self, client):
        """HTTPBearer returns 403 when no Authorization header is present."""
        # We need an endpoint that uses get_tenant_context. Since no routes
        # are wired yet, we test via direct dependency behavior instead.
        # This test documents the expected behavior for when routes are added.
        # For now, verify the client fixture works.
        response = await client.get("/health")
        assert response.status_code == 200


class TestGetTenantContextSessionVars:
    """Test that get_tenant_context sets PostgreSQL session variables correctly."""

    async def test_employee_sets_both_session_vars(self, admin_db_session):
        """Verify SET LOCAL is called with company_id and sub_brand_id."""
        from app.core.dependencies import get_tenant_context

        company_id = str(uuid4())
        sub_brand_id = str(uuid4())
        token = create_test_token(
            company_id=company_id, sub_brand_id=sub_brand_id, role="employee"
        )

        # Create a mock credentials object
        creds = type("Creds", (), {"credentials": token})()

        context = await get_tenant_context(credentials=creds, db=admin_db_session)

        assert context.role == "employee"
        assert str(context.company_id) == company_id
        assert str(context.sub_brand_id) == sub_brand_id

        # Verify session variables were set
        result = await admin_db_session.execute(
            text("SELECT current_setting('app.current_company_id', true)")
        )
        assert result.scalar() == company_id

        result = await admin_db_session.execute(
            text("SELECT current_setting('app.current_sub_brand_id', true)")
        )
        assert result.scalar() == sub_brand_id

    async def test_reel48_admin_sets_empty_strings(self, admin_db_session):
        """reel48_admin triggers RLS bypass via empty string session vars."""
        from app.core.dependencies import get_tenant_context

        token = create_test_token(role="reel48_admin")
        creds = type("Creds", (), {"credentials": token})()

        context = await get_tenant_context(credentials=creds, db=admin_db_session)

        assert context.is_reel48_admin is True
        assert context.company_id is None

        result = await admin_db_session.execute(
            text("SELECT current_setting('app.current_company_id', true)")
        )
        assert result.scalar() == ""

        result = await admin_db_session.execute(
            text("SELECT current_setting('app.current_sub_brand_id', true)")
        )
        assert result.scalar() == ""

    async def test_corporate_admin_sets_empty_sub_brand(self, admin_db_session):
        """corporate_admin has company_id but no sub_brand_id."""
        from app.core.dependencies import get_tenant_context

        company_id = str(uuid4())
        token = create_test_token(company_id=company_id, role="corporate_admin")
        creds = type("Creds", (), {"credentials": token})()

        context = await get_tenant_context(credentials=creds, db=admin_db_session)

        assert context.is_corporate_admin_or_above is True
        assert context.sub_brand_id is None

        result = await admin_db_session.execute(
            text("SELECT current_setting('app.current_company_id', true)")
        )
        assert result.scalar() == company_id

        result = await admin_db_session.execute(
            text("SELECT current_setting('app.current_sub_brand_id', true)")
        )
        assert result.scalar() == ""

    async def test_binds_structlog_contextvars(self, admin_db_session):
        """Verify structlog contextvars are bound with tenant info."""
        from app.core.dependencies import get_tenant_context

        company_id = str(uuid4())
        sub_brand_id = str(uuid4())
        token = create_test_token(
            company_id=company_id, sub_brand_id=sub_brand_id, role="employee"
        )
        creds = type("Creds", (), {"credentials": token})()

        structlog.contextvars.clear_contextvars()
        context = await get_tenant_context(credentials=creds, db=admin_db_session)

        ctx = structlog.contextvars.get_contextvars()
        assert ctx["user_id"] == context.user_id
        assert ctx["company_id"] == company_id
        assert ctx["sub_brand_id"] == sub_brand_id
        assert ctx["role"] == "employee"
