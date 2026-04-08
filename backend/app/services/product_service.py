from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_product(
        self,
        data: ProductCreate,
        company_id: UUID,
        sub_brand_id: UUID | None,
        created_by: UUID,
    ) -> Product:
        # Check SKU uniqueness within company (excluding soft-deleted)
        await self._check_sku_unique(data.sku, company_id)

        product = Product(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            created_by=created_by,
            **data.model_dump(),
        )
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def get_product(
        self, product_id: UUID, company_id: UUID | None = None
    ) -> Product:
        query = select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
        if company_id is not None:
            query = query.where(Product.company_id == company_id)
        result = await self.db.execute(query)
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundError("Product", str(product_id))
        return product

    async def list_products(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
        status_filter: str | None = None,
        active_only: bool = False,
    ) -> tuple[list[Product], int]:
        query = select(Product).where(
            Product.company_id == company_id,
            Product.deleted_at.is_(None),
        )
        if sub_brand_id is not None:
            query = query.where(Product.sub_brand_id == sub_brand_id)
        if active_only:
            query = query.where(Product.status == "active")
        elif status_filter is not None:
            query = query.where(Product.status == status_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def update_product(
        self, product_id: UUID, company_id: UUID, data: ProductUpdate
    ) -> Product:
        product = await self.get_product(product_id, company_id)
        if product.status != "draft":
            raise ForbiddenError("Only draft products can be updated")

        update_data = data.model_dump(exclude_unset=True)

        # If SKU is being changed, validate uniqueness
        if "sku" in update_data and update_data["sku"] != product.sku:
            await self._check_sku_unique(
                update_data["sku"], company_id, exclude_id=product_id
            )

        for field, value in update_data.items():
            setattr(product, field, value)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def submit_product(
        self, product_id: UUID, company_id: UUID
    ) -> Product:
        product = await self.get_product(product_id, company_id)
        if product.status != "draft":
            raise ForbiddenError("Only draft products can be submitted for approval")
        product.status = "submitted"  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def soft_delete_product(
        self, product_id: UUID, company_id: UUID
    ) -> Product:
        product = await self.get_product(product_id, company_id)
        if product.status != "draft":
            raise ForbiddenError("Only draft products can be deleted")
        product.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def _check_sku_unique(
        self,
        sku: str,
        company_id: UUID,
        exclude_id: UUID | None = None,
    ) -> None:
        query = select(Product.id).where(
            Product.company_id == company_id,
            Product.sku == sku,
            Product.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(Product.id != exclude_id)
        result = await self.db.execute(query)
        if result.scalar_one_or_none() is not None:
            raise ConflictError(f"A product with SKU '{sku}' already exists in this company")
