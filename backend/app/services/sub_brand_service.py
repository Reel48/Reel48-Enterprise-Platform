from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.sub_brand import SubBrand
from app.schemas.sub_brand import SubBrandCreate, SubBrandUpdate


class SubBrandService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sub_brands(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
    ) -> tuple[list[SubBrand], int]:
        query = select(SubBrand).where(
            SubBrand.company_id == company_id,
            SubBrand.is_active == True,  # noqa: E712
        )
        if sub_brand_id is not None:
            query = query.where(SubBrand.id == sub_brand_id)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_sub_brand(self, sub_brand_id: UUID, company_id: UUID) -> SubBrand:
        result = await self.db.execute(
            select(SubBrand).where(
                SubBrand.id == sub_brand_id,
                SubBrand.company_id == company_id,
            )
        )
        sub_brand = result.scalar_one_or_none()
        if sub_brand is None:
            raise NotFoundError("SubBrand", str(sub_brand_id))
        return sub_brand

    async def create_sub_brand(self, company_id: UUID, data: SubBrandCreate) -> SubBrand:
        # Check slug uniqueness within company
        existing = await self.db.execute(
            select(SubBrand).where(
                SubBrand.company_id == company_id,
                SubBrand.slug == data.slug,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(
                f"Sub-brand with slug '{data.slug}' already exists in this company"
            )

        sub_brand = SubBrand(company_id=company_id, name=data.name, slug=data.slug)
        self.db.add(sub_brand)
        await self.db.flush()
        await self.db.refresh(sub_brand)
        return sub_brand

    async def update_sub_brand(
        self, sub_brand_id: UUID, company_id: UUID, data: SubBrandUpdate
    ) -> SubBrand:
        sub_brand = await self.get_sub_brand(sub_brand_id, company_id)

        if data.slug is not None and data.slug != sub_brand.slug:
            existing = await self.db.execute(
                select(SubBrand).where(
                    SubBrand.company_id == company_id,
                    SubBrand.slug == data.slug,
                    SubBrand.id != sub_brand_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError(
                    f"Sub-brand with slug '{data.slug}' already exists in this company"
                )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(sub_brand, field, value)
        await self.db.flush()
        await self.db.refresh(sub_brand)
        return sub_brand

    async def deactivate_sub_brand(self, sub_brand_id: UUID, company_id: UUID) -> SubBrand:
        sub_brand = await self.get_sub_brand(sub_brand_id, company_id)

        if sub_brand.is_default:
            raise ConflictError("Cannot deactivate the default sub-brand")

        # Check it's not the last active sub-brand
        active_count = await self.db.scalar(
            select(func.count()).where(
                SubBrand.company_id == company_id,
                SubBrand.is_active == True,  # noqa: E712
            )
        )
        if active_count is not None and active_count <= 1:
            raise ConflictError("Cannot deactivate the last active sub-brand")

        sub_brand.is_active = False  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(sub_brand)
        return sub_brand
