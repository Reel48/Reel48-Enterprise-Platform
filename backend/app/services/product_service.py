from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

MAX_PRODUCT_IMAGES = 10


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

    async def list_all_products(
        self,
        page: int,
        per_page: int,
        status_filter: str | None = None,
        company_id_filter: UUID | None = None,
    ) -> tuple[list[Product], int]:
        """List products across ALL companies. For reel48_admin platform endpoints."""
        query = select(Product).where(Product.deleted_at.is_(None))
        if status_filter is not None:
            query = query.where(Product.status == status_filter)
        if company_id_filter is not None:
            query = query.where(Product.company_id == company_id_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def approve_product(
        self, product_id: UUID, approved_by: UUID
    ) -> Product:
        """submitted → approved. Sets approved_by and approved_at."""
        product = await self.get_product(product_id)
        if product.status != "submitted":
            raise ForbiddenError("Only submitted products can be approved")
        product.status = "approved"  # type: ignore[assignment]
        product.approved_by = approved_by  # type: ignore[assignment]
        product.approved_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def reject_product(self, product_id: UUID) -> Product:
        """submitted → draft. Clears approval fields."""
        product = await self.get_product(product_id)
        if product.status != "submitted":
            raise ForbiddenError("Only submitted products can be rejected")
        product.status = "draft"  # type: ignore[assignment]
        product.approved_by = None  # type: ignore[assignment]
        product.approved_at = None  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def activate_product(self, product_id: UUID) -> Product:
        """approved → active. Makes product visible to employees."""
        product = await self.get_product(product_id)
        if product.status != "approved":
            raise ForbiddenError("Only approved products can be activated")
        product.status = "active"  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def add_product_image(
        self,
        product_id: UUID,
        s3_key: str,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> Product:
        """Add an image S3 key to a product's image_urls array."""
        product = await self.get_product(product_id, company_id)

        if product.status != "draft":
            raise ForbiddenError("Images can only be managed on draft products")

        # Sub-brand scoping: non-corporate admins can only manage their sub-brand's products
        if (
            sub_brand_id is not None
            and product.sub_brand_id is not None
            and product.sub_brand_id != sub_brand_id
        ):
            raise ForbiddenError("You can only manage images for products in your sub-brand")

        # Validate s3_key starts with the correct company_id prefix
        if not s3_key.startswith(f"{company_id}/"):
            raise ForbiddenError("S3 key does not match your company scope")

        # Validate s3_key is in the products category path
        parts = s3_key.split("/")
        if len(parts) < 4 or parts[2] != "products":
            raise ValidationError("S3 key must be in the products category path")

        # Check image limit
        current_urls = list(product.image_urls) if product.image_urls else []
        if len(current_urls) >= MAX_PRODUCT_IMAGES:
            raise ValidationError(
                f"Product cannot have more than {MAX_PRODUCT_IMAGES} images"
            )

        # Append and reassign (SQLAlchemy doesn't detect in-place JSONB mutations)
        current_urls.append(s3_key)
        product.image_urls = current_urls  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def remove_product_image(
        self,
        product_id: UUID,
        index: int,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> Product:
        """Remove an image URL from a product's image_urls array by index."""
        product = await self.get_product(product_id, company_id)

        if product.status != "draft":
            raise ForbiddenError("Images can only be managed on draft products")

        # Sub-brand scoping
        if (
            sub_brand_id is not None
            and product.sub_brand_id is not None
            and product.sub_brand_id != sub_brand_id
        ):
            raise ForbiddenError("You can only manage images for products in your sub-brand")

        current_urls = list(product.image_urls) if product.image_urls else []
        if index < 0 or index >= len(current_urls):
            raise ValidationError(
                f"Image index {index} is out of bounds (product has {len(current_urls)} images)"
            )

        current_urls.pop(index)
        product.image_urls = current_urls  # type: ignore[assignment]
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
