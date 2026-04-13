from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.sub_brand import SubBrand
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

if TYPE_CHECKING:
    from app.services.cognito_service import CognitoService

VALID_ROLES = {"employee", "regional_manager", "sub_brand_admin", "corporate_admin"}
ADMIN_ASSIGNABLE_ROLES = {"sub_brand_admin", "corporate_admin"}


class UserService:
    def __init__(self, db: AsyncSession, cognito_service: CognitoService | None = None):
        self.db = db
        self.cognito_service = cognito_service

    async def list_users(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
    ) -> tuple[list[User], int]:
        query = select(User).where(
            User.company_id == company_id,
            User.deleted_at.is_(None),
        )
        if sub_brand_id is not None:
            query = query.where(User.sub_brand_id == sub_brand_id)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_user(self, user_id: UUID, company_id: UUID | None = None) -> User:
        query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        if company_id is not None:
            query = query.where(User.company_id == company_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def get_user_by_cognito_sub(self, cognito_sub: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.cognito_sub == cognito_sub,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_user(
        self, company_id: UUID, data: UserCreate, context_role: str
    ) -> User:
        # Validate role
        if data.role not in VALID_ROLES:
            raise ValidationError(f"Invalid role: {data.role}", field="role")
        if data.role == "reel48_admin":
            raise ForbiddenError("Cannot assign reel48_admin role via this endpoint")
        if data.role in ADMIN_ASSIGNABLE_ROLES and context_role not in (
            "reel48_admin",
            "corporate_admin",
        ):
            raise ForbiddenError(
                f"Only corporate_admin or above can assign the {data.role} role"
            )

        # Email uniqueness
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"User with email '{data.email}' already exists")

        # Validate sub_brand_id belongs to company
        sb_result = await self.db.execute(
            select(SubBrand).where(
                SubBrand.id == data.sub_brand_id,
                SubBrand.company_id == company_id,
            )
        )
        if sb_result.scalar_one_or_none() is None:
            raise ValidationError(
                "sub_brand_id does not belong to this company", field="sub_brand_id"
            )

        # Create Cognito user if service is available (Phase 5+)
        if self.cognito_service is not None:
            temp_password = secrets.token_urlsafe(16) + "A1!"
            cognito_sub = await self.cognito_service.create_cognito_user(
                email=data.email,
                temporary_password=temp_password,
                company_id=company_id,
                sub_brand_id=data.sub_brand_id,
                role=data.role,
            )
        else:
            cognito_sub = str(uuid4())  # Placeholder for tests without Cognito mock

        user = User(
            company_id=company_id,
            sub_brand_id=data.sub_brand_id,
            cognito_sub=cognito_sub,
            email=data.email,
            full_name=data.full_name,
            role=data.role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_user(
        self,
        user_id: UUID,
        company_id: UUID | None,
        data: UserUpdate,
        context_role: str,
    ) -> User:
        user = await self.get_user(user_id, company_id)

        update_data = data.model_dump(exclude_unset=True)

        # Role change validation
        if "role" in update_data:
            new_role = update_data["role"]
            if new_role not in VALID_ROLES:
                raise ValidationError(f"Invalid role: {new_role}", field="role")
            if new_role == "reel48_admin":
                raise ForbiddenError("Cannot assign reel48_admin role via this endpoint")
            if new_role in ADMIN_ASSIGNABLE_ROLES and context_role not in (
                "reel48_admin",
                "corporate_admin",
            ):
                raise ForbiddenError(
                    f"Only corporate_admin or above can assign the {new_role} role"
                )

        # Sub-brand change validation
        if "sub_brand_id" in update_data and update_data["sub_brand_id"] is not None:
            sb_result = await self.db.execute(
                select(SubBrand).where(
                    SubBrand.id == update_data["sub_brand_id"],
                    SubBrand.company_id == user.company_id,
                )
            )
            if sb_result.scalar_one_or_none() is None:
                raise ValidationError(
                    "sub_brand_id does not belong to this company", field="sub_brand_id"
                )

        # Email uniqueness check
        if "email" in update_data:
            new_email = update_data["email"]
            existing = await self.db.execute(
                select(User).where(User.email == new_email, User.id != user_id)
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError(f"Email '{new_email}' is already in use")

        for field, value in update_data.items():
            setattr(user, field, value)
        await self.db.flush()
        await self.db.refresh(user)

        # Sync updated attributes to Cognito
        if self.cognito_service is not None:
            cognito_attrs: dict[str, str] = {}
            if "full_name" in update_data:
                cognito_attrs["name"] = update_data["full_name"]
            if "email" in update_data:
                cognito_attrs["email"] = update_data["email"]
            if cognito_attrs:
                await self.cognito_service.update_cognito_attributes(
                    user.cognito_sub, cognito_attrs  # type: ignore[arg-type]
                )

        return user

    async def soft_delete_user(self, user_id: UUID, company_id: UUID) -> User:
        user = await self.get_user(user_id, company_id)
        user.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(user)

        # Disable Cognito user if service is available
        if self.cognito_service is not None:
            await self.cognito_service.disable_cognito_user(user.cognito_sub)  # type: ignore[arg-type]

        return user
