"""
Registration service — business logic for employee onboarding flows.

Handles both self-registration (via org code) and invite-based registration.
All validation, Cognito calls, and DB inserts are encapsulated here;
the auth router stays thin.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.company import Company
from app.models.invite import Invite
from app.models.org_code import OrgCode
from app.models.sub_brand import SubBrand
from app.models.user import User
from app.services.cognito_service import CognitoService

logger = structlog.get_logger()


class RegistrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_org_code(
        self, code: str
    ) -> tuple[OrgCode, Company, list[SubBrand]]:
        """
        Validate an org code and return the associated company + sub-brands.

        Raises AppException on any failure (invalid code, inactive, etc.).
        """
        result = await self.db.execute(
            select(OrgCode).where(OrgCode.code == code, OrgCode.is_active.is_(True))
        )
        org_code = result.scalar_one_or_none()
        if org_code is None:
            raise AppException(
                code="INVALID_REQUEST",
                message="Invalid registration code",
                status_code=400,
            )

        company_result = await self.db.execute(
            select(Company).where(Company.id == org_code.company_id)
        )
        company = company_result.scalar_one_or_none()
        if company is None or not company.is_active:
            raise AppException(
                code="INVALID_REQUEST",
                message="Invalid registration code",
                status_code=400,
            )

        sb_result = await self.db.execute(
            select(SubBrand)
            .where(
                SubBrand.company_id == company.id,
                SubBrand.is_active.is_(True),
            )
            .order_by(SubBrand.is_default.desc(), SubBrand.name.asc())
        )
        sub_brands = list(sb_result.scalars().all())

        return org_code, company, sub_brands

    async def register_via_org_code(
        self,
        code: str,
        sub_brand_id: UUID,
        email: str,
        full_name: str,
        password: str,
        cognito_service: CognitoService,
    ) -> User:
        """
        Self-registration flow via org code.

        Validates the code, sub-brand ownership, email uniqueness,
        creates the Cognito user, and inserts the local User record.
        """
        # 1. Validate org code
        org_code, company, _sub_brands = await self.validate_org_code(code)

        # 2. Validate sub_brand_id belongs to the resolved company
        sb_result = await self.db.execute(
            select(SubBrand).where(
                SubBrand.id == sub_brand_id,
                SubBrand.company_id == company.id,
                SubBrand.is_active.is_(True),
            )
        )
        if sb_result.scalar_one_or_none() is None:
            raise AppException(
                code="REGISTRATION_FAILED",
                message="Registration failed",
                status_code=400,
            )

        # 3. Check email uniqueness in local DB
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise AppException(
                code="REGISTRATION_FAILED",
                message="Registration failed",
                status_code=400,
            )

        # 4. Create Cognito user with permanent password
        cognito_sub = await cognito_service.create_cognito_user_with_password(
            email=email,
            password=password,
            company_id=company.id,  # type: ignore[arg-type]
            sub_brand_id=sub_brand_id,
            role="employee",
        )

        # 5. Create local user record
        user = User(
            company_id=company.id,
            sub_brand_id=sub_brand_id,
            cognito_sub=cognito_sub,
            email=email,
            full_name=full_name,
            role="employee",
            registration_method="self_registration",
            org_code_id=org_code.id,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        logger.info(
            "user_self_registered",
            user_id=str(user.id),
            company_id=str(company.id),
            sub_brand_id=str(sub_brand_id),
        )

        return user

    async def register_via_invite(
        self,
        token: str,
        email: str,
        full_name: str,
        password: str,
        cognito_service: CognitoService,
    ) -> User:
        """
        Invite-based registration flow.

        Validates the invite token (not expired, not consumed, email match),
        creates the Cognito user, inserts the local User record, and marks
        the invite as consumed.
        """
        now = datetime.now(UTC)

        # 1. Look up invite by token
        result = await self.db.execute(
            select(Invite).where(
                Invite.token == token,
                Invite.consumed_at.is_(None),
                Invite.expires_at > now,
            )
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise AppException(
                code="REGISTRATION_FAILED",
                message="Registration failed",
                status_code=400,
            )

        # 2. Verify email matches (case-insensitive)
        if invite.email.lower() != email.lower():
            raise AppException(
                code="REGISTRATION_FAILED",
                message="Registration failed",
                status_code=400,
            )

        # 3. Check email uniqueness in local DB
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise AppException(
                code="REGISTRATION_FAILED",
                message="Registration failed",
                status_code=400,
            )

        # 4. Create Cognito user with permanent password
        cognito_sub = await cognito_service.create_cognito_user_with_password(
            email=email,
            password=password,
            company_id=invite.company_id,  # type: ignore[arg-type]
            sub_brand_id=invite.target_sub_brand_id,  # type: ignore[arg-type]
            role=invite.role,  # type: ignore[arg-type]
        )

        # 5. Create local user record
        user = User(
            company_id=invite.company_id,
            sub_brand_id=invite.target_sub_brand_id,
            cognito_sub=cognito_sub,
            email=email,
            full_name=full_name,
            role=invite.role,
            registration_method="invite",
        )
        self.db.add(user)
        await self.db.flush()

        # 6. Mark invite as consumed
        invite.consumed_at = now  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(user)

        logger.info(
            "user_registered_via_invite",
            user_id=str(user.id),
            company_id=str(invite.company_id),
            sub_brand_id=str(invite.target_sub_brand_id),
            invite_id=str(invite.id),
        )

        return user
