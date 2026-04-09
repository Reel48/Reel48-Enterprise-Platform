from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.schemas.bulk_order import BulkOrderCreate, BulkOrderUpdate


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
