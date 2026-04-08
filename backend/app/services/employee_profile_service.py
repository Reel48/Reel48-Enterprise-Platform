from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.employee_profile import EmployeeProfile
from app.schemas.employee_profile import EmployeeProfileCreate, EmployeeProfileUpdate


class EmployeeProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(
        self,
        user_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        data: EmployeeProfileCreate,
    ) -> EmployeeProfile:
        existing = await self.db.execute(
            select(EmployeeProfile).where(
                EmployeeProfile.user_id == user_id,
                EmployeeProfile.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Profile already exists for user {user_id}")

        profile = EmployeeProfile(
            user_id=user_id,
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            **data.model_dump(exclude_unset=True),
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def get_profile_by_user_id(
        self, user_id: UUID, company_id: UUID | None = None
    ) -> EmployeeProfile:
        query = select(EmployeeProfile).where(
            EmployeeProfile.user_id == user_id,
            EmployeeProfile.deleted_at.is_(None),
        )
        if company_id is not None:
            query = query.where(EmployeeProfile.company_id == company_id)
        result = await self.db.execute(query)
        profile = result.scalar_one_or_none()
        if profile is None:
            raise NotFoundError("EmployeeProfile", str(user_id))
        return profile

    async def get_profile(
        self, profile_id: UUID, company_id: UUID | None = None
    ) -> EmployeeProfile:
        query = select(EmployeeProfile).where(
            EmployeeProfile.id == profile_id,
            EmployeeProfile.deleted_at.is_(None),
        )
        if company_id is not None:
            query = query.where(EmployeeProfile.company_id == company_id)
        result = await self.db.execute(query)
        profile = result.scalar_one_or_none()
        if profile is None:
            raise NotFoundError("EmployeeProfile", str(profile_id))
        return profile

    async def update_profile(
        self,
        profile_id: UUID,
        company_id: UUID,
        data: EmployeeProfileUpdate,
    ) -> EmployeeProfile:
        profile = await self.get_profile(profile_id, company_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def list_profiles(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
    ) -> tuple[list[EmployeeProfile], int]:
        query = select(EmployeeProfile).where(
            EmployeeProfile.company_id == company_id,
            EmployeeProfile.deleted_at.is_(None),
        )
        if sub_brand_id is not None:
            query = query.where(EmployeeProfile.sub_brand_id == sub_brand_id)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def soft_delete_profile(
        self, profile_id: UUID, company_id: UUID
    ) -> EmployeeProfile:
        profile = await self.get_profile(profile_id, company_id)
        profile.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def upsert_my_profile(
        self,
        user_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        data: EmployeeProfileCreate,
    ) -> EmployeeProfile:
        result = await self.db.execute(
            select(EmployeeProfile).where(
                EmployeeProfile.user_id == user_id,
                EmployeeProfile.deleted_at.is_(None),
            )
        )
        profile = result.scalar_one_or_none()

        if profile is not None:
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(profile, field, value)
        else:
            profile = EmployeeProfile(
                user_id=user_id,
                company_id=company_id,
                sub_brand_id=sub_brand_id,
                **data.model_dump(exclude_unset=True),
            )
            self.db.add(profile)

        await self.db.flush()
        await self.db.refresh(profile)
        return profile
