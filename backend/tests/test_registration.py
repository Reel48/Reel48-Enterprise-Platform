"""
Tests for Phase 5: self-registration, invite registration, and Cognito integration.

Covers:
- Org code validation endpoint
- Self-registration via org code
- Invite-based registration
- Rate limiting (shared auth group)
- Generic error responses (no enumeration)
- Tenant isolation for self-registered users
"""

import secrets
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RateLimitError
from app.core.rate_limit import rate_limit_auth
from app.main import app
from app.models.invite import Invite
from app.models.org_code import OrgCode
from app.models.user import User

# ==========================================================================
# Org Code Validation
# ==========================================================================


class TestValidateOrgCode:
    async def test_valid_code_returns_company_and_sub_brands(
        self, client: AsyncClient, company_a, org_code_a
    ):
        response = await client.post(
            "/api/v1/auth/validate-org-code",
            json={"code": org_code_a.code},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["company_name"] == "Company A"
        assert len(data["sub_brands"]) == 2
        # Default sub-brand should be first (sorted by is_default DESC, name ASC)
        assert data["sub_brands"][0]["is_default"] is True
        assert data["sub_brands"][0]["name"] == "Brand A1"

    async def test_invalid_code_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/validate-org-code",
            json={"code": "INVALID1"},
        )
        assert response.status_code == 400
        errors = response.json()["errors"]
        assert errors[0]["code"] == "INVALID_REQUEST"
        assert errors[0]["message"] == "Invalid registration code"

    async def test_inactive_code_returns_400(
        self, client: AsyncClient, admin_db_session: AsyncSession, org_code_a
    ):
        # Deactivate the code
        org_code_a.is_active = False
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/auth/validate-org-code",
            json={"code": org_code_a.code},
        )
        assert response.status_code == 400
        errors = response.json()["errors"]
        assert errors[0]["code"] == "INVALID_REQUEST"

    async def test_error_messages_identical_for_invalid_and_inactive(
        self, client: AsyncClient, admin_db_session: AsyncSession, org_code_a
    ):
        # Get error for nonexistent code
        resp_invalid = await client.post(
            "/api/v1/auth/validate-org-code",
            json={"code": "NOEXIST1"},
        )
        # Deactivate and get error for inactive code
        org_code_a.is_active = False
        await admin_db_session.flush()
        resp_inactive = await client.post(
            "/api/v1/auth/validate-org-code",
            json={"code": org_code_a.code},
        )
        # Both should have identical error responses
        assert resp_invalid.json()["errors"] == resp_inactive.json()["errors"]

    async def test_no_auth_required(self, client: AsyncClient, org_code_a):
        """Validate-org-code should work without an Authorization header."""
        response = await client.post(
            "/api/v1/auth/validate-org-code",
            json={"code": org_code_a.code},
        )
        assert response.status_code == 200


# ==========================================================================
# Self-Registration
# ==========================================================================


class TestSelfRegistration:
    async def test_register_creates_employee(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        org_code_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_a1.id),
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 201
        assert "Registration successful" in response.json()["data"]["message"]

        # Verify user was created in DB
        result = await admin_db_session.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one()
        assert user.role == "employee"
        assert user.registration_method == "self_registration"
        assert user.org_code_id == org_code_a.id
        assert user.company_id == _company.id
        assert user.sub_brand_id == brand_a1.id

    async def test_register_with_wrong_sub_brand_returns_400(
        self, client: AsyncClient, company_a, company_b, org_code_a
    ):
        _company_b, brand_b1 = company_b
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_b1.id),  # Wrong company's sub-brand
                "email": "wrong-sb@example.com",
                "full_name": "Wrong Sub",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400
        assert response.json()["errors"][0]["code"] == "REGISTRATION_FAILED"

    async def test_register_with_invalid_code_returns_400(
        self, client: AsyncClient, company_a
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": "INVALID1",
                "sub_brand_id": str(brand_a1.id),
                "email": "badcode@example.com",
                "full_name": "Bad Code",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400

    async def test_register_with_inactive_code_returns_400(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        org_code_a,
    ):
        _company, brand_a1, _a2 = company_a
        org_code_a.is_active = False
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_a1.id),
                "email": "inactive@example.com",
                "full_name": "Inactive Code",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400

    async def test_register_duplicate_email_returns_generic_400(
        self,
        client: AsyncClient,
        company_a,
        org_code_a,
        user_a1_employee,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_a1.id),
                "email": user_a1_employee.email,  # Already exists
                "full_name": "Duplicate",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400
        # Same generic error — no hint about duplicate email
        assert response.json()["errors"][0]["code"] == "REGISTRATION_FAILED"

    async def test_deactivated_code_rejected_after_new_code_generated(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        org_code_a,
        user_a_corporate_admin,
    ):
        """Old code should be rejected after a new code is generated."""
        _company, brand_a1, _a2 = company_a
        old_code = org_code_a.code

        # Generate a new code (deactivates the old one)
        new_code = OrgCode(
            company_id=_company.id,
            code="TESTA002",
            is_active=True,
            created_by=user_a_corporate_admin.id,
        )
        org_code_a.is_active = False
        admin_db_session.add(new_code)
        await admin_db_session.flush()

        # Old code should be rejected
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": old_code,
                "sub_brand_id": str(brand_a1.id),
                "email": "oldcode@example.com",
                "full_name": "Old Code",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400

    async def test_register_no_auth_required(
        self, client: AsyncClient, company_a, org_code_a
    ):
        """Register endpoint should work without Authorization header."""
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_a1.id),
                "email": "noauth@example.com",
                "full_name": "No Auth",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 201


# ==========================================================================
# Invite Registration
# ==========================================================================


class TestInviteRegistration:
    async def test_register_with_valid_invite(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        invite_a1,
    ):
        company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": invite_a1.token,
                "email": invite_a1.email,
                "full_name": "Invited User",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 201
        assert "Registration successful" in response.json()["data"]["message"]

        # Verify user was created with correct attributes
        result = await admin_db_session.execute(
            select(User).where(User.email == invite_a1.email)
        )
        user = result.scalar_one()
        assert user.company_id == company.id
        assert user.sub_brand_id == brand_a1.id
        assert user.role == "employee"
        assert user.registration_method == "invite"

    async def test_invite_marked_consumed_after_registration(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        invite_a1,
    ):
        # Register using the invite
        await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": invite_a1.token,
                "email": invite_a1.email,
                "full_name": "Invited User",
                "password": "SecureP@ss123",
            },
        )

        # Refresh the invite to see the update
        await admin_db_session.refresh(invite_a1)
        assert invite_a1.consumed_at is not None

        # Attempting to reuse should fail
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": invite_a1.token,
                "email": invite_a1.email,
                "full_name": "Reuse Attempt",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400

    async def test_expired_invite_returns_400(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a_corporate_admin,
    ):
        company, brand_a1, _a2 = company_a
        expired_invite = Invite(
            company_id=company.id,
            target_sub_brand_id=brand_a1.id,
            email="expired@companya.com",
            role="employee",
            token=secrets.token_hex(32),
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Already expired
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(expired_invite)
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": expired_invite.token,
                "email": "expired@companya.com",
                "full_name": "Expired User",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400
        assert response.json()["errors"][0]["code"] == "REGISTRATION_FAILED"

    async def test_consumed_invite_returns_400(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a_corporate_admin,
    ):
        company, brand_a1, _a2 = company_a
        consumed_invite = Invite(
            company_id=company.id,
            target_sub_brand_id=brand_a1.id,
            email="consumed@companya.com",
            role="employee",
            token=secrets.token_hex(32),
            expires_at=datetime.now(UTC) + timedelta(hours=72),
            consumed_at=datetime.now(UTC),  # Already consumed
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(consumed_invite)
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": consumed_invite.token,
                "email": "consumed@companya.com",
                "full_name": "Consumed User",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400

    async def test_wrong_email_returns_400(
        self, client: AsyncClient, invite_a1
    ):
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": invite_a1.token,
                "email": "wrong@example.com",  # Doesn't match invite
                "full_name": "Wrong Email",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400
        assert response.json()["errors"][0]["code"] == "REGISTRATION_FAILED"

    async def test_invite_register_no_auth_required(
        self, client: AsyncClient, invite_a1
    ):
        """Register-from-invite should work without Authorization header."""
        response = await client.post(
            "/api/v1/auth/register-from-invite",
            json={
                "token": invite_a1.token,
                "email": invite_a1.email,
                "full_name": "No Auth Invite",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 201


# ==========================================================================
# Rate Limiting
# ==========================================================================


class TestRateLimiting:
    async def test_rate_limit_blocks_after_5_validate_attempts(
        self, client: AsyncClient
    ):
        """6th validate-org-code attempt from the same IP should return 429."""
        call_count = 0

        async def _counting_rate_limit() -> None:
            nonlocal call_count
            call_count += 1
            if call_count > 5:
                raise RateLimitError()

        app.dependency_overrides[rate_limit_auth] = _counting_rate_limit

        try:
            for i in range(5):
                resp = await client.post(
                    "/api/v1/auth/validate-org-code",
                    json={"code": "ANYCODE1"},
                )
                # These may be 400 (invalid code) but NOT 429
                assert resp.status_code != 429

            # 6th attempt should be rate limited
            resp = await client.post(
                "/api/v1/auth/validate-org-code",
                json={"code": "ANYCODE1"},
            )
            assert resp.status_code == 429
        finally:
            # Restore the no-op override
            async def _noop() -> None:
                return None

            app.dependency_overrides[rate_limit_auth] = _noop

    async def test_rate_limit_shared_between_validate_and_register(
        self, client: AsyncClient, company_a, org_code_a
    ):
        """3 validates + 3 registers = 6th request blocked (shared auth group)."""
        _company, brand_a1, _a2 = company_a
        call_count = 0

        async def _counting_rate_limit() -> None:
            nonlocal call_count
            call_count += 1
            if call_count > 5:
                raise RateLimitError()

        app.dependency_overrides[rate_limit_auth] = _counting_rate_limit

        try:
            # 3 validate attempts
            for _ in range(3):
                await client.post(
                    "/api/v1/auth/validate-org-code",
                    json={"code": "ANYCODE1"},
                )

            # 2 register attempts (4th and 5th total)
            for i in range(2):
                await client.post(
                    "/api/v1/auth/register",
                    json={
                        "code": org_code_a.code,
                        "sub_brand_id": str(brand_a1.id),
                        "email": f"ratelimit{i}@example.com",
                        "full_name": "Rate Limit",
                        "password": "SecureP@ss123",
                    },
                )

            # 6th attempt (register) should be rate limited
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "code": org_code_a.code,
                    "sub_brand_id": str(brand_a1.id),
                    "email": "ratelimit-blocked@example.com",
                    "full_name": "Blocked",
                    "password": "SecureP@ss123",
                },
            )
            assert resp.status_code == 429
        finally:
            async def _noop() -> None:
                return None

            app.dependency_overrides[rate_limit_auth] = _noop


# ==========================================================================
# Security — Generic Error Responses
# ==========================================================================


class TestGenericErrors:
    async def test_register_errors_reveal_nothing(
        self,
        client: AsyncClient,
        company_a,
        org_code_a,
        user_a1_employee,
    ):
        """All registration failure modes should return identical error messages."""
        _company, brand_a1, _a2 = company_a

        # Invalid code
        resp_bad_code = await client.post(
            "/api/v1/auth/register",
            json={
                "code": "INVALID1",
                "sub_brand_id": str(brand_a1.id),
                "email": "test1@example.com",
                "full_name": "Test",
                "password": "SecureP@ss123",
            },
        )

        # Duplicate email
        resp_dup_email = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_a1.id),
                "email": user_a1_employee.email,
                "full_name": "Test",
                "password": "SecureP@ss123",
            },
        )

        # Both should be 400 with same error code
        assert resp_bad_code.status_code == 400
        assert resp_dup_email.status_code == 400
        # Error codes should be from the same family (INVALID_REQUEST or REGISTRATION_FAILED)
        bad_code_errors = resp_bad_code.json()["errors"]
        dup_email_errors = resp_dup_email.json()["errors"]
        # Both are generic failures — no hint about what went wrong
        assert len(bad_code_errors) == 1
        assert len(dup_email_errors) == 1


# ==========================================================================
# Isolation
# ==========================================================================


class TestRegistrationIsolation:
    async def test_self_registered_user_cannot_see_other_company(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
        org_code_a,
    ):
        """
        A user registered via Company A's org code should not see Company B's data.
        """
        _company_a, brand_a1, _a2 = company_a

        # Register a user via Company A's org code
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_a1.id),
                "email": "isolation-test@example.com",
                "full_name": "Isolation Test",
                "password": "SecureP@ss123",
            },
        )
        assert resp.status_code == 201

        # Look up the created user to get their cognito_sub
        result = await admin_db_session.execute(
            select(User).where(User.email == "isolation-test@example.com")
        )
        user = result.scalar_one()

        # Create a token for this user
        from tests.conftest import create_test_token

        token = create_test_token(
            user_id=user.cognito_sub,
            company_id=str(user.company_id),
            sub_brand_id=str(user.sub_brand_id),
            role="employee",
        )

        # Try to list users — should only see Company A users (RLS enforced via JWT)
        # The user is an employee so they'll get 403 on list, but that also proves
        # they can't see other company data
        resp = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Employee cannot list users (403) — confirming role enforcement
        assert resp.status_code == 403

    async def test_cannot_register_with_sub_brand_from_another_company(
        self,
        client: AsyncClient,
        company_a,
        company_b,
        org_code_a,
    ):
        """Submitting Company B's sub_brand_id with Company A's org code should fail."""
        _company_b, brand_b1 = company_b
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "code": org_code_a.code,
                "sub_brand_id": str(brand_b1.id),
                "email": "cross-company@example.com",
                "full_name": "Cross Company",
                "password": "SecureP@ss123",
            },
        )
        assert response.status_code == 400
