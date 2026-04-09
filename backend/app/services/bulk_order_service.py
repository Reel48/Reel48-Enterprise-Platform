from __future__ import annotations

import secrets
from decimal import Decimal
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.product import Product
from app.models.user import User
from app.schemas.bulk_order import (
    BulkOrderCreate,
    BulkOrderItemCreate,
    BulkOrderItemUpdate,
    BulkOrderUpdate,
)


class BulkOrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_bulk_order(
        self,
        data: BulkOrderCreate,
        company_id: UUID,
        sub_brand_id: UUID | None,
        created_by: UUID,
    ) -> BulkOrder:
        """Create a new draft bulk order session."""
        # 1. Validate catalog
        await self._validate_catalog(data.catalog_id, company_id)

        # 2. Generate unique order number
        order_number = await self._generate_bulk_order_number()

        # 3. Create the bulk order record
        bulk_order = BulkOrder(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            catalog_id=data.catalog_id,
            created_by=created_by,
            title=data.title,
            description=data.description,
            order_number=order_number,
            status="draft",
            total_items=0,
            total_amount=0,
            notes=data.notes,
        )
        self.db.add(bulk_order)
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def update_bulk_order(
        self,
        bulk_order_id: UUID,
        data: BulkOrderUpdate,
        company_id: UUID,
    ) -> BulkOrder:
        """Update a draft bulk order session (title, description, notes)."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)

        if bulk_order.status != "draft":
            raise ForbiddenError("Only draft bulk orders can be edited")

        if data.title is not None:
            bulk_order.title = data.title
        if data.description is not None:
            bulk_order.description = data.description
        if data.notes is not None:
            bulk_order.notes = data.notes

        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def delete_bulk_order(
        self,
        bulk_order_id: UUID,
        company_id: UUID,
    ) -> None:
        """Hard-delete a draft bulk order and all its items."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)

        if bulk_order.status != "draft":
            raise ForbiddenError("Only draft bulk orders can be deleted")

        # Delete items first (FK dependency), then the bulk order
        await self.db.execute(
            delete(BulkOrderItem).where(
                BulkOrderItem.bulk_order_id == bulk_order_id
            )
        )
        await self.db.execute(
            delete(BulkOrder).where(BulkOrder.id == bulk_order_id)
        )
        await self.db.flush()

    async def get_bulk_order(
        self,
        bulk_order_id: UUID,
        company_id: UUID | None = None,
    ) -> BulkOrder:
        """Fetch a single bulk order by ID with optional company_id filter."""
        query = select(BulkOrder).where(BulkOrder.id == bulk_order_id)
        if company_id is not None:
            query = query.where(BulkOrder.company_id == company_id)
        result = await self.db.execute(query)
        bulk_order = result.scalar_one_or_none()
        if bulk_order is None:
            raise NotFoundError("BulkOrder", str(bulk_order_id))
        return bulk_order

    async def get_bulk_order_items(
        self,
        bulk_order_id: UUID,
    ) -> list[BulkOrderItem]:
        """Get all items for a bulk order, ordered by created_at."""
        result = await self.db.execute(
            select(BulkOrderItem)
            .where(BulkOrderItem.bulk_order_id == bulk_order_id)
            .order_by(BulkOrderItem.created_at)
        )
        return list(result.scalars().all())

    async def list_bulk_orders(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
        status_filter: str | None = None,
    ) -> tuple[list[BulkOrder], int]:
        """List bulk orders within the user's tenant scope."""
        query = select(BulkOrder).where(BulkOrder.company_id == company_id)

        if sub_brand_id is not None:
            query = query.where(BulkOrder.sub_brand_id == sub_brand_id)
        if status_filter is not None:
            query = query.where(BulkOrder.status == status_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(BulkOrder.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    async def add_item(
        self,
        bulk_order_id: UUID,
        data: BulkOrderItemCreate,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> BulkOrderItem:
        """Add an item to a draft bulk order with product/employee validation."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "draft":
            raise ForbiddenError("Can only add items to draft bulk orders")

        # Validate product is in the catalog
        cp_result = await self.db.execute(
            select(CatalogProduct).where(
                CatalogProduct.catalog_id == bulk_order.catalog_id,
                CatalogProduct.product_id == data.product_id,
            )
        )
        catalog_product = cp_result.scalar_one_or_none()
        if catalog_product is None:
            raise NotFoundError("Product", str(data.product_id))

        # Fetch product — must exist and be active
        prod_result = await self.db.execute(
            select(Product).where(
                Product.id == data.product_id,
                Product.deleted_at.is_(None),
            )
        )
        product = prod_result.scalar_one_or_none()
        if product is None:
            raise NotFoundError("Product", str(data.product_id))
        if product.status != "active":
            raise ValidationError(
                f"Product '{product.name}' is not active (status: {product.status})"
            )

        # Resolve price: catalog override or product price
        unit_price: Decimal
        if catalog_product.price_override is not None:
            unit_price = Decimal(str(catalog_product.price_override))
        else:
            unit_price = Decimal(str(product.unit_price))

        # Validate size
        if data.size is not None and product.sizes:
            if data.size not in product.sizes:
                raise ValidationError(
                    f"Invalid size '{data.size}' for product '{product.name}'. "
                    f"Available sizes: {product.sizes}"
                )

        # Validate decoration
        if data.decoration is not None and product.decoration_options:
            if data.decoration not in product.decoration_options:
                raise ValidationError(
                    f"Invalid decoration '{data.decoration}' for product '{product.name}'. "
                    f"Available options: {product.decoration_options}"
                )

        # Validate employee if provided (company_id match only — not sub_brand)
        if data.employee_id is not None:
            emp_result = await self.db.execute(
                select(User).where(
                    User.id == data.employee_id,
                    User.company_id == company_id,
                )
            )
            if emp_result.scalar_one_or_none() is None:
                raise ValidationError("Employee not found in this company")

        line_total = unit_price * data.quantity

        item = BulkOrderItem(
            company_id=bulk_order.company_id,
            sub_brand_id=bulk_order.sub_brand_id,
            bulk_order_id=bulk_order_id,
            employee_id=data.employee_id,
            product_id=data.product_id,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=unit_price,
            quantity=data.quantity,
            size=data.size,
            decoration=data.decoration,
            line_total=line_total,
            notes=data.notes,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)

        await self._recalculate_totals(bulk_order_id)
        return item

    async def update_item(
        self,
        bulk_order_id: UUID,
        item_id: UUID,
        data: BulkOrderItemUpdate,
        company_id: UUID,
    ) -> BulkOrderItem:
        """Update an item within a draft bulk order."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "draft":
            raise ForbiddenError("Can only edit items in draft bulk orders")

        result = await self.db.execute(
            select(BulkOrderItem).where(
                BulkOrderItem.id == item_id,
                BulkOrderItem.bulk_order_id == bulk_order_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("BulkOrderItem", str(item_id))

        # Lazy-load the product only if size/decoration validation is needed
        product: Product | None = None

        async def _get_product() -> Product:
            nonlocal product
            if product is None:
                prod_result = await self.db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = prod_result.scalar_one_or_none()
                if product is None:
                    raise NotFoundError("Product", str(item.product_id))
            return product

        if data.quantity is not None:
            item.quantity = data.quantity
            item.line_total = Decimal(str(item.unit_price)) * data.quantity

        if data.size is not None:
            p = await _get_product()
            if p.sizes and data.size not in p.sizes:
                raise ValidationError(
                    f"Invalid size '{data.size}' for product '{p.name}'. "
                    f"Available sizes: {p.sizes}"
                )
            item.size = data.size

        if data.decoration is not None:
            p = await _get_product()
            if p.decoration_options and data.decoration not in p.decoration_options:
                raise ValidationError(
                    f"Invalid decoration '{data.decoration}' for product '{p.name}'. "
                    f"Available options: {p.decoration_options}"
                )
            item.decoration = data.decoration

        if data.employee_id is not None:
            emp_result = await self.db.execute(
                select(User).where(
                    User.id == data.employee_id,
                    User.company_id == company_id,
                )
            )
            if emp_result.scalar_one_or_none() is None:
                raise ValidationError("Employee not found in this company")
            item.employee_id = data.employee_id

        if data.notes is not None:
            item.notes = data.notes

        await self.db.flush()
        await self.db.refresh(item)

        await self._recalculate_totals(bulk_order_id)
        return item

    async def remove_item(
        self,
        bulk_order_id: UUID,
        item_id: UUID,
        company_id: UUID,
    ) -> None:
        """Remove an item from a draft bulk order (hard delete)."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "draft":
            raise ForbiddenError("Can only remove items from draft bulk orders")

        result = await self.db.execute(
            select(BulkOrderItem).where(
                BulkOrderItem.id == item_id,
                BulkOrderItem.bulk_order_id == bulk_order_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("BulkOrderItem", str(item_id))

        await self.db.execute(
            delete(BulkOrderItem).where(BulkOrderItem.id == item_id)
        )
        await self.db.flush()

        await self._recalculate_totals(bulk_order_id)

    async def _recalculate_totals(self, bulk_order_id: UUID) -> None:
        """Recalculate denormalized total_items and total_amount on a bulk order."""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(BulkOrderItem.quantity), 0),
                func.coalesce(func.sum(BulkOrderItem.line_total), Decimal("0")),
            ).where(BulkOrderItem.bulk_order_id == bulk_order_id)
        )
        row = result.one()
        total_items = int(row[0])
        total_amount = row[1]

        bulk_order_result = await self.db.execute(
            select(BulkOrder).where(BulkOrder.id == bulk_order_id)
        )
        bulk_order = bulk_order_result.scalar_one()
        bulk_order.total_items = total_items
        bulk_order.total_amount = total_amount
        await self.db.flush()
        await self.db.refresh(bulk_order)

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    async def submit_bulk_order(
        self, bulk_order_id: UUID, company_id: UUID,
    ) -> BulkOrder:
        """Submit a draft bulk order for approval.

        Guards:
        1. Must be in 'draft' status
        2. Must have at least one item
        3. Records submitted_at timestamp
        """
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "draft":
            raise ForbiddenError("Only draft bulk orders can be submitted")

        item_count = await self.db.scalar(
            select(func.count()).select_from(
                select(BulkOrderItem.id).where(
                    BulkOrderItem.bulk_order_id == bulk_order_id
                ).subquery()
            )
        )
        if item_count == 0:
            raise ValidationError("Cannot submit a bulk order with no items")

        bulk_order.status = "submitted"
        bulk_order.submitted_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def approve_bulk_order(
        self, bulk_order_id: UUID, company_id: UUID, approved_by: UUID,
    ) -> BulkOrder:
        """Approve a submitted bulk order. Records approved_by and approved_at."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "submitted":
            raise ForbiddenError("Only submitted bulk orders can be approved")
        bulk_order.status = "approved"
        bulk_order.approved_by = approved_by
        bulk_order.approved_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def process_bulk_order(
        self, bulk_order_id: UUID, company_id: UUID,
    ) -> BulkOrder:
        """Mark an approved bulk order as processing."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "approved":
            raise ForbiddenError("Only approved bulk orders can be marked as processing")
        bulk_order.status = "processing"
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def ship_bulk_order(
        self, bulk_order_id: UUID, company_id: UUID,
    ) -> BulkOrder:
        """Mark a processing bulk order as shipped."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "processing":
            raise ForbiddenError("Only processing bulk orders can be shipped")
        bulk_order.status = "shipped"
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def deliver_bulk_order(
        self, bulk_order_id: UUID, company_id: UUID,
    ) -> BulkOrder:
        """Mark a shipped bulk order as delivered."""
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
        if bulk_order.status != "shipped":
            raise ForbiddenError("Only shipped bulk orders can be delivered")
        bulk_order.status = "delivered"
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    async def cancel_bulk_order(
        self,
        bulk_order_id: UUID,
        company_id: UUID,
        cancelled_by_user_id: UUID,
        is_manager_or_above: bool,
    ) -> BulkOrder:
        """Cancel a draft, submitted, or approved bulk order.

        Authorization:
        - draft: creator or manager_or_above
        - submitted/approved: manager_or_above only
        - processing/shipped/delivered/cancelled: cannot cancel
        """
        bulk_order = await self.get_bulk_order(bulk_order_id, company_id)

        if bulk_order.status == "draft":
            if not is_manager_or_above and bulk_order.created_by != cancelled_by_user_id:
                raise ForbiddenError("Only the creator or a manager can cancel this bulk order")
        elif bulk_order.status in ("submitted", "approved"):
            if not is_manager_or_above:
                raise ForbiddenError("Only managers can cancel submitted or approved bulk orders")
        else:
            raise ForbiddenError(f"Cannot cancel a bulk order with status '{bulk_order.status}'")

        bulk_order.status = "cancelled"
        bulk_order.cancelled_at = datetime.now(UTC)
        bulk_order.cancelled_by = cancelled_by_user_id
        await self.db.flush()
        await self.db.refresh(bulk_order)
        return bulk_order

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _validate_catalog(
        self, catalog_id: UUID, company_id: UUID
    ) -> Catalog:
        """Validate catalog exists, belongs to company, is active, and buying window is open."""
        result = await self.db.execute(
            select(Catalog).where(
                Catalog.id == catalog_id,
                Catalog.company_id == company_id,
                Catalog.deleted_at.is_(None),
            )
        )
        catalog = result.scalar_one_or_none()
        if catalog is None:
            raise NotFoundError("Catalog", str(catalog_id))
        if catalog.status != "active":
            raise ForbiddenError("Catalog is not active")

        # Check buying window for invoice_after_close catalogs
        if catalog.payment_model == "invoice_after_close":
            now = datetime.now(UTC)
            if catalog.buying_window_opens_at and catalog.buying_window_opens_at > now:
                raise ValidationError("Buying window is not open yet")
            if catalog.buying_window_closes_at and catalog.buying_window_closes_at < now:
                raise ValidationError("Buying window has closed")

        return catalog

    async def _generate_bulk_order_number(self) -> str:
        """Generate a unique order number: BLK-YYYYMMDD-XXXX."""
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        for _ in range(5):
            random_part = secrets.token_hex(2).upper()
            order_number = f"BLK-{date_str}-{random_part}"
            result = await self.db.execute(
                select(BulkOrder.id).where(
                    BulkOrder.order_number == order_number
                )
            )
            if result.scalar_one_or_none() is None:
                return order_number
        raise ValidationError(
            "Could not generate a unique bulk order number. Please try again."
        )
