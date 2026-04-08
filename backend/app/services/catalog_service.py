from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.product import Product
from app.schemas.catalog import CatalogCreate, CatalogUpdate


def _slugify(name: str) -> str:
    """Generate a URL-safe slug from a name.

    Lowercase, replace non-alphanumeric characters with hyphens,
    collapse consecutive hyphens, strip leading/trailing hyphens.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "catalog"


class CatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_catalog(
        self,
        data: CatalogCreate,
        company_id: UUID,
        sub_brand_id: UUID | None,
        created_by: UUID,
    ) -> Catalog:
        # Validate buying window ordering if both dates provided
        if (
            data.buying_window_opens_at is not None
            and data.buying_window_closes_at is not None
            and data.buying_window_opens_at >= data.buying_window_closes_at
        ):
            raise ValidationError("buying_window_opens_at must be before buying_window_closes_at")

        slug = await self._unique_slug(data.name, company_id)

        catalog = Catalog(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            created_by=created_by,
            name=data.name,
            description=data.description,
            slug=slug,
            payment_model=data.payment_model,
            buying_window_opens_at=data.buying_window_opens_at,
            buying_window_closes_at=data.buying_window_closes_at,
        )
        self.db.add(catalog)
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def get_catalog(
        self, catalog_id: UUID, company_id: UUID | None = None
    ) -> Catalog:
        query = select(Catalog).where(
            Catalog.id == catalog_id,
            Catalog.deleted_at.is_(None),
        )
        if company_id is not None:
            query = query.where(Catalog.company_id == company_id)
        result = await self.db.execute(query)
        catalog = result.scalar_one_or_none()
        if catalog is None:
            raise NotFoundError("Catalog", str(catalog_id))
        return catalog

    async def list_catalogs(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
        status_filter: str | None = None,
        active_only: bool = False,
    ) -> tuple[list[Catalog], int]:
        query = select(Catalog).where(
            Catalog.company_id == company_id,
            Catalog.deleted_at.is_(None),
        )
        if sub_brand_id is not None:
            query = query.where(Catalog.sub_brand_id == sub_brand_id)
        if active_only:
            query = query.where(Catalog.status == "active")
        elif status_filter is not None:
            query = query.where(Catalog.status == status_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def update_catalog(
        self, catalog_id: UUID, company_id: UUID, data: CatalogUpdate
    ) -> Catalog:
        catalog = await self.get_catalog(catalog_id, company_id)
        if catalog.status != "draft":
            raise ForbiddenError("Only draft catalogs can be updated")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(catalog, field, value)

        # Re-validate buying window if dates changed
        opens = catalog.buying_window_opens_at
        closes = catalog.buying_window_closes_at
        if opens is not None and closes is not None and opens >= closes:
            raise ValidationError("buying_window_opens_at must be before buying_window_closes_at")

        # If name changed, regenerate slug
        if "name" in update_data:
            catalog.slug = await self._unique_slug(  # type: ignore[assignment]
                update_data["name"], company_id, exclude_id=catalog_id
            )

        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def submit_catalog(
        self, catalog_id: UUID, company_id: UUID
    ) -> Catalog:
        catalog = await self.get_catalog(catalog_id, company_id)
        if catalog.status != "draft":
            raise ForbiddenError("Only draft catalogs can be submitted for approval")

        # Must have at least one product
        product_count = await self.db.scalar(
            select(func.count()).select_from(
                select(CatalogProduct).where(
                    CatalogProduct.catalog_id == catalog_id
                ).subquery()
            )
        )
        if not product_count:
            raise ValidationError("Cannot submit a catalog with no products")

        catalog.status = "submitted"  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def soft_delete_catalog(
        self, catalog_id: UUID, company_id: UUID
    ) -> Catalog:
        catalog = await self.get_catalog(catalog_id, company_id)
        if catalog.status != "draft":
            raise ForbiddenError("Only draft catalogs can be deleted")

        # Hard delete junction entries
        junction_rows = await self.db.execute(
            select(CatalogProduct).where(CatalogProduct.catalog_id == catalog_id)
        )
        for row in junction_rows.scalars().all():
            await self.db.delete(row)

        catalog.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def add_product_to_catalog(
        self,
        catalog_id: UUID,
        product_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        display_order: int,
        price_override: float | None,
    ) -> CatalogProduct:
        # Verify catalog exists and belongs to same company
        catalog = await self.get_catalog(catalog_id, company_id)

        # Verify product exists and belongs to same company
        product_result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.deleted_at.is_(None),
            )
        )
        product = product_result.scalar_one_or_none()
        if product is None:
            raise NotFoundError("Product", str(product_id))
        if product.company_id != company_id:
            raise ForbiddenError("Cannot add a product from a different company")

        # Check for duplicate
        existing = await self.db.execute(
            select(CatalogProduct.id).where(
                CatalogProduct.catalog_id == catalog_id,
                CatalogProduct.product_id == product_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Product is already in this catalog")

        catalog_product = CatalogProduct(
            catalog_id=catalog_id,
            product_id=product_id,
            company_id=catalog.company_id,
            sub_brand_id=catalog.sub_brand_id,
            display_order=display_order,
            price_override=price_override,
        )
        self.db.add(catalog_product)
        await self.db.flush()
        await self.db.refresh(catalog_product)
        return catalog_product

    async def remove_product_from_catalog(
        self, catalog_id: UUID, product_id: UUID, company_id: UUID
    ) -> None:
        # Verify catalog exists and is draft
        catalog = await self.get_catalog(catalog_id, company_id)
        if catalog.status != "draft":
            raise ForbiddenError("Can only remove products from draft catalogs")

        result = await self.db.execute(
            select(CatalogProduct).where(
                CatalogProduct.catalog_id == catalog_id,
                CatalogProduct.product_id == product_id,
            )
        )
        cp = result.scalar_one_or_none()
        if cp is None:
            raise NotFoundError("CatalogProduct", f"{catalog_id}/{product_id}")

        await self.db.delete(cp)
        await self.db.flush()

    async def list_catalog_products(
        self,
        catalog_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
    ) -> tuple[list[CatalogProduct], int]:
        # Verify catalog exists
        await self.get_catalog(catalog_id, company_id)

        query = select(CatalogProduct).where(
            CatalogProduct.catalog_id == catalog_id,
            CatalogProduct.company_id == company_id,
        )
        if sub_brand_id is not None:
            query = query.where(CatalogProduct.sub_brand_id == sub_brand_id)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(CatalogProduct.display_order).offset(
            (page - 1) * per_page
        ).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def list_all_catalogs(
        self,
        page: int,
        per_page: int,
        status_filter: str | None = None,
        company_id_filter: UUID | None = None,
    ) -> tuple[list[Catalog], int]:
        """List catalogs across ALL companies. For reel48_admin platform endpoints."""
        query = select(Catalog).where(Catalog.deleted_at.is_(None))
        if status_filter is not None:
            query = query.where(Catalog.status == status_filter)
        if company_id_filter is not None:
            query = query.where(Catalog.company_id == company_id_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def approve_catalog(
        self, catalog_id: UUID, approved_by: UUID
    ) -> Catalog:
        """submitted → approved. All products in catalog must be approved or active."""
        catalog = await self.get_catalog(catalog_id)
        if catalog.status != "submitted":
            raise ForbiddenError("Only submitted catalogs can be approved")

        # Verify all products in catalog are approved or active
        cp_rows = await self.db.execute(
            select(CatalogProduct.product_id).where(
                CatalogProduct.catalog_id == catalog_id
            )
        )
        product_ids = [row[0] for row in cp_rows.all()]
        if product_ids:
            products = await self.db.execute(
                select(Product.id, Product.status).where(Product.id.in_(product_ids))
            )
            for pid, pstatus in products.all():
                if pstatus not in ("approved", "active"):
                    raise ValidationError(
                        f"Product {pid} has status '{pstatus}'. "
                        "All products must be approved or active before catalog approval."
                    )

        catalog.status = "approved"  # type: ignore[assignment]
        catalog.approved_by = approved_by  # type: ignore[assignment]
        catalog.approved_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def reject_catalog(self, catalog_id: UUID) -> Catalog:
        """submitted → draft. Clears approval fields."""
        catalog = await self.get_catalog(catalog_id)
        if catalog.status != "submitted":
            raise ForbiddenError("Only submitted catalogs can be rejected")
        catalog.status = "draft"  # type: ignore[assignment]
        catalog.approved_by = None  # type: ignore[assignment]
        catalog.approved_at = None  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def activate_catalog(self, catalog_id: UUID) -> Catalog:
        """approved → active. Makes catalog visible to employees."""
        catalog = await self.get_catalog(catalog_id)
        if catalog.status != "approved":
            raise ForbiddenError("Only approved catalogs can be activated")
        catalog.status = "active"  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def close_catalog(self, catalog_id: UUID) -> Catalog:
        """active → closed. For buying window catalogs."""
        catalog = await self.get_catalog(catalog_id)
        if catalog.status != "active":
            raise ForbiddenError("Only active catalogs can be closed")
        catalog.status = "closed"  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(catalog)
        return catalog

    async def _unique_slug(
        self, name: str, company_id: UUID, exclude_id: UUID | None = None
    ) -> str:
        """Generate a unique slug within the company, appending -2, -3, etc. on collision."""
        base_slug = _slugify(name)
        slug = base_slug
        suffix = 2

        while True:
            query = select(Catalog.id).where(
                Catalog.company_id == company_id,
                Catalog.slug == slug,
                Catalog.deleted_at.is_(None),
            )
            if exclude_id is not None:
                query = query.where(Catalog.id != exclude_id)
            result = await self.db.execute(query)
            if result.scalar_one_or_none() is None:
                return slug
            slug = f"{base_slug}-{suffix}"
            suffix += 1
