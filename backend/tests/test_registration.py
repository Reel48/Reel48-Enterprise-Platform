"""Tests for the RegistrationService (single-step org-code flow + invite flow)."""

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.registration_service import RegistrationService


@pytest.mark.asyncio
async def test_register_via_org_code_creates_user(
    admin_db_session, org_code_a, mock_cognito
) -> None:
    service = RegistrationService(admin_db_session)
    user = await service.register_via_org_code(
        code=org_code_a.code,
        email="newhire@companya.com",
        full_name="New Hire",
        password="Valid-Passw0rd!",
        cognito_service=mock_cognito,
    )
    assert user.role == "employee"
    assert user.registration_method == "self_registration"
    assert user.org_code_id == org_code_a.id


@pytest.mark.asyncio
async def test_register_via_invite_marks_consumed(
    admin_db_session, invite_a, mock_cognito
) -> None:
    service = RegistrationService(admin_db_session)
    user = await service.register_via_invite(
        token=invite_a.token,
        email=invite_a.email,
        full_name="Invitee",
        password="Valid-Passw0rd!",
        cognito_service=mock_cognito,
    )
    assert user.role == "employee"
    assert user.registration_method == "invite"

    await admin_db_session.refresh(invite_a)
    assert invite_a.consumed_at is not None


@pytest.mark.asyncio
async def test_register_via_invite_email_mismatch(
    admin_db_session, invite_a, mock_cognito
) -> None:
    service = RegistrationService(admin_db_session)
    with pytest.raises(Exception):
        await service.register_via_invite(
            token=invite_a.token,
            email="wrong@x.com",
            full_name="Wrong",
            password="Valid-Passw0rd!",
            cognito_service=mock_cognito,
        )


@pytest.mark.asyncio
async def test_validate_org_code_returns_company(
    admin_db_session, org_code_a, company_a
) -> None:
    service = RegistrationService(admin_db_session)
    org_code, company = await service.validate_org_code(org_code_a.code)
    assert org_code.id == org_code_a.id
    assert company.id == company_a.id


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(
    admin_db_session, org_code_a, mock_cognito
) -> None:
    service = RegistrationService(admin_db_session)
    await service.register_via_org_code(
        code=org_code_a.code,
        email="dupe@companya.com",
        full_name="First",
        password="Valid-Passw0rd!",
        cognito_service=mock_cognito,
    )
    with pytest.raises(Exception):
        await service.register_via_org_code(
            code=org_code_a.code,
            email="dupe@companya.com",
            full_name="Second",
            password="Valid-Passw0rd!",
            cognito_service=mock_cognito,
        )
    result = await admin_db_session.execute(
        select(User).where(User.email == "dupe@companya.com")
    )
    assert len(list(result.scalars())) == 1
