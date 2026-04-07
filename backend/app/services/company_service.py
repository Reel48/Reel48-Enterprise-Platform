from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company
from app.models.sub_brand import SubBrand
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_companies(
        self,
        company_id: UUID | None,
        page: int,
        per_page: int,
    ) -> tuple[list[Company], int]:
        query = select(Company)
        if company_id is not None:
            query = query.where(Company.id == company_id)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_company(self, company_id: UUID) -> Company:
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if company is None:
            raise NotFoundError("Company", str(company_id))
        return company

    async def create_company(self, data: CompanyCreate) -> Company:
        # Check slug uniqueness
        existing = await self.db.execute(
            select(Company).where(Company.slug == data.slug)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Company with slug '{data.slug}' already exists")

        # Create company
        company = Company(name=data.name, slug=data.slug)
        self.db.add(company)
        await self.db.flush()

        # Atomically create default sub-brand (ADR-003)
        default_sub_brand = SubBrand(
            company_id=company.id,
            name=f"{company.name} - Default",
            slug="default",
            is_default=True,
        )
        self.db.add(default_sub_brand)
        await self.db.flush()
        await self.db.refresh(company)

        return company

    async def update_company(self, company_id: UUID, data: CompanyUpdate) -> Company:
        company = await self.get_company(company_id)

        if data.slug is not None and data.slug != company.slug:
            existing = await self.db.execute(
                select(Company).where(Company.slug == data.slug, Company.id != company_id)
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError(f"Company with slug '{data.slug}' already exists")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        await self.db.flush()
        await self.db.refresh(company)
        return company

    async def deactivate_company(self, company_id: UUID) -> Company:
        company = await self.get_company(company_id)
        company.is_active = False  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(company)
        return company
