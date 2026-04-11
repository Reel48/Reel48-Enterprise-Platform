import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company
from app.models.sub_brand import SubBrand
from app.schemas.company import CompanyCreate, CompanyUpdate


def _slugify(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "company"


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

    async def list_all_companies(
        self,
        page: int,
        per_page: int,
        is_active: bool | None = None,
    ) -> tuple[list[Company], int]:
        """List all companies across the platform with optional is_active filter."""
        query = select(Company)
        if is_active is not None:
            query = query.where(Company.is_active == is_active)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.order_by(Company.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_company(self, company_id: UUID) -> Company:
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if company is None:
            raise NotFoundError("Company", str(company_id))
        return company

    async def _resolve_unique_slug(self, base_slug: str) -> str:
        """Return a unique slug, appending -2, -3, etc. on collision."""
        slug = base_slug
        suffix = 1
        while True:
            existing = await self.db.execute(
                select(Company).where(Company.slug == slug)
            )
            if existing.scalar_one_or_none() is None:
                return slug
            suffix += 1
            slug = f"{base_slug}-{suffix}"

    async def create_company(self, data: CompanyCreate) -> Company:
        # Auto-generate slug from name if not provided
        base_slug = data.slug if data.slug else _slugify(data.name)
        slug = await self._resolve_unique_slug(base_slug)

        # Create company
        company = Company(name=data.name, slug=slug)
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

    async def reactivate_company(self, company_id: UUID) -> Company:
        company = await self.get_company(company_id)
        company.is_active = True  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(company)
        return company
