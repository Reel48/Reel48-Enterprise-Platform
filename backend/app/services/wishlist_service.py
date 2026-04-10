"""Wishlist service — add, remove, list, and check products in employee wishlists."""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.catalog import Catalog
from app.models.product import Product
from app.models.wishlist import Wishlist
from app.schemas.wishlist import WishlistCreate

logger = structlog.get_logger()


class WishlistService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add_to_wishlist(
        self,
        user_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        data: WishlistCreate,
    ) -> dict:
        """Add a product to the user's wishlist.

        Validates:
        - Product exists and belongs to the same company
        - Product is active (status='active')
        - Not already in the user's wishlist (UNIQUE constraint on user_id+product_id)
        If catalog_id is provided, validates the catalog exists and contains the product.
        Returns dict with wishlist entry + product details for response serialization.
        """
        # Validate product exists, belongs to same company, and is active
        result = await self.db.execute(
            select(Product).where(
                Product.id == data.product_id,
                Product.company_id == company_id,
                Product.deleted_at.is_(None),
            )
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundError("Product", str(data.product_id))

        if product.status != "active":
            raise ForbiddenError("Only active products can be added to wishlist")

        # Validate catalog if provided
        if data.catalog_id is not None:
            cat_result = await self.db.execute(
                select(Catalog.id).where(
                    Catalog.id == data.catalog_id,
                    Catalog.company_id == company_id,
                    Catalog.deleted_at.is_(None),
                )
            )
            if cat_result.scalar_one_or_none() is None:
                raise NotFoundError("Catalog", str(data.catalog_id))

        # Check for duplicate
        existing = await self.db.execute(
            select(Wishlist.id).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == data.product_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Product is already in your wishlist")

        wishlist_entry = Wishlist(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            user_id=user_id,
            product_id=data.product_id,
            catalog_id=data.catalog_id,
            notes=data.notes,
        )
        self.db.add(wishlist_entry)
        await self.db.flush()
        await self.db.refresh(wishlist_entry)

        logger.info(
            "wishlist_item_added",
            wishlist_id=str(wishlist_entry.id),
            product_id=str(data.product_id),
            user_id=str(user_id),
        )

        return self._build_response(wishlist_entry, product)

    async def remove_from_wishlist(
        self,
        wishlist_id: UUID,
        user_id: UUID,
    ) -> None:
        """Remove a product from the user's wishlist. Hard delete.

        Validates the wishlist entry belongs to the requesting user.
        """
        result = await self.db.execute(
            select(Wishlist).where(Wishlist.id == wishlist_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None or entry.user_id != user_id:
            raise NotFoundError("Wishlist entry", str(wishlist_id))

        await self.db.delete(entry)
        await self.db.flush()

        logger.info(
            "wishlist_item_removed",
            wishlist_id=str(wishlist_id),
            user_id=str(user_id),
        )

    async def list_wishlist(
        self,
        user_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        """List the user's wishlist with product details.

        Joins wishlists -> products to include product name, SKU, unit_price,
        image_urls, status. Orders by created_at DESC (most recently added first).
        Returns (list of response dicts, total count).
        """
        base_query = select(Wishlist, Product).join(
            Product, Wishlist.product_id == Product.id
        ).where(
            Wishlist.user_id == user_id,
            Wishlist.company_id == company_id,
        )

        if sub_brand_id is not None:
            base_query = base_query.where(Wishlist.sub_brand_id == sub_brand_id)

        # Count
        count_query = select(func.count()).select_from(
            base_query.with_only_columns(Wishlist.id).subquery()
        )
        total = await self.db.scalar(count_query) or 0

        # Paginate
        query = base_query.order_by(Wishlist.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        rows = result.all()

        items = [self._build_response(w, p) for w, p in rows]
        return items, total

    async def check_wishlist(
        self,
        user_id: UUID,
        product_ids: list[UUID],
    ) -> dict[str, bool]:
        """Check if multiple products are in the user's wishlist.

        Returns a dict mapping product_id (str) -> is_wishlisted (bool).
        """
        if not product_ids:
            return {}

        result = await self.db.execute(
            select(Wishlist.product_id).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id.in_(product_ids),
            )
        )
        wishlisted = {row[0] for row in result.all()}

        return {str(pid): pid in wishlisted for pid in product_ids}

    @staticmethod
    def _build_response(entry: Wishlist, product: Product) -> dict:
        """Build a response dict from a wishlist entry and its product."""
        image_urls = product.image_urls or []
        return {
            "id": entry.id,
            "product_id": entry.product_id,
            "catalog_id": entry.catalog_id,
            "product_name": product.name,
            "product_sku": product.sku,
            "product_unit_price": float(product.unit_price),
            "product_image_url": image_urls[0] if image_urls else None,
            "product_status": product.status,
            "is_purchasable": product.status == "active" and product.deleted_at is None,
            "notes": entry.notes,
            "created_at": entry.created_at,
        }
