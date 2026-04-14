"""
Invoice lifecycle management service.

Orchestrates invoice creation across all three billing flows (assigned,
self-service, post-window), Stripe integration, webhook handling, and
tenant-scoped queries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.models.company import Company
from app.models.invoice import Invoice
from app.models.sub_brand import SubBrand
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.services.stripe_service import StripeService

logger = structlog.get_logger()

# Valid status transitions — used by webhook handlers to enforce ordering
_STATUS_ORDER = {
    "draft": 0,
    "finalized": 1,
    "sent": 2,
    "paid": 3,
    "payment_failed": 2,  # Same level as sent (can happen after sent)
    "voided": 4,          # Terminal — can happen from draft or finalized
}


class InvoiceService:
    """Core business logic for invoice lifecycle management."""

    def __init__(
        self,
        db: AsyncSession,
        stripe_service: StripeService | None = None,
    ) -> None:
        self.db = db
        self._stripe = stripe_service

    # ═══════════════════════════════════════════════════════════════════════
    # Platform Admin Operations (reel48_admin only)
    # ═══════════════════════════════════════════════════════════════════════

    async def create_assigned_invoice(
        self,
        company_id: UUID,
        created_by: UUID,
        order_ids: list[UUID] | None = None,
        bulk_order_ids: list[UUID] | None = None,
        sub_brand_id: UUID | None = None,
    ) -> Invoice:
        """Flow 1: Create an assigned invoice for a client company from specific orders.

        - Looks up the company and its stripe_customer_id (creates if needed)
        - Creates a draft Stripe Invoice
        - Adds line items from the referenced orders/bulk orders
        - Creates the local Invoice record
        - Returns the Invoice with stripe_invoice_id populated
        """
        if not order_ids and not bulk_order_ids:
            raise ValidationError("At least one order_id or bulk_order_id is required")

        company = await self._get_company(company_id)
        stripe_customer_id = await self._ensure_stripe_customer(company)

        # Resolve sub_brand_id from first order if not provided
        resolved_sub_brand_id = sub_brand_id

        # Gather line items from orders
        line_items_data: list[dict] = []
        total = Decimal("0")

        if order_ids:
            for order_id in order_ids:
                order = await self._get_order(order_id, company_id)
                if resolved_sub_brand_id is None:
                    resolved_sub_brand_id = order.sub_brand_id
                items = await self._get_order_line_items(order_id)
                for item in items:
                    line_items_data.append({
                        "description": f"{item.product_name} ({item.product_sku}) x{item.quantity}",
                        "quantity": item.quantity,
                        "unit_amount_cents": int(item.unit_price * 100),
                    })
                    total += item.line_total

        if bulk_order_ids:
            for bulk_order_id in bulk_order_ids:
                bulk_order = await self._get_bulk_order(bulk_order_id, company_id)
                if resolved_sub_brand_id is None:
                    resolved_sub_brand_id = bulk_order.sub_brand_id
                items = await self._get_bulk_order_items(bulk_order_id)
                for item in items:
                    line_items_data.append({
                        "description": f"{item.product_name} ({item.product_sku}) x{item.quantity}",
                        "quantity": item.quantity,
                        "unit_amount_cents": int(item.unit_price * 100),
                    })
                    total += item.line_total

        # Create Stripe invoice + line items
        metadata = {
            "reel48_company_id": str(company_id),
            "reel48_created_by": str(created_by),
            "billing_flow": "assigned",
        }
        if resolved_sub_brand_id:
            metadata["reel48_sub_brand_id"] = str(resolved_sub_brand_id)

        stripe_invoice = await self._stripe.create_invoice(
            customer_id=stripe_customer_id,
            metadata=metadata,
            auto_advance=False,
        )

        for li in line_items_data:
            await self._stripe.create_invoice_item(
                customer_id=stripe_customer_id,
                invoice_id=stripe_invoice["id"],
                description=li["description"],
                quantity=li["quantity"],
                unit_amount_cents=li["unit_amount_cents"],
            )

        # Create local invoice record
        invoice = Invoice(
            company_id=company_id,
            sub_brand_id=resolved_sub_brand_id,
            order_id=order_ids[0] if order_ids and len(order_ids) == 1 else None,
            bulk_order_id=bulk_order_ids[0] if bulk_order_ids and len(bulk_order_ids) == 1 else None,
            stripe_invoice_id=stripe_invoice["id"],
            stripe_invoice_url=stripe_invoice.get("hosted_invoice_url"),
            billing_flow="assigned",
            status="draft",
            total_amount=total,
            created_by=created_by,
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info(
            "invoice_created",
            invoice_id=str(invoice.id),
            billing_flow="assigned",
            company_id=str(company_id),
            total_amount=str(total),
        )
        return invoice

    async def create_post_window_invoice(
        self,
        catalog_id: UUID,
        created_by: UUID,
    ) -> Invoice:
        """Flow 3: Create a consolidated invoice after a buying window closes.

        - Validates the catalog exists and has payment_model = 'invoice_after_close'
        - Validates the buying window has closed (buying_window_closes_at < now)
        - Gathers all approved orders placed against this catalog
        - Creates a single Stripe Invoice with all line items
        - Creates the local Invoice record with billing_flow = 'post_window'
        """
        catalog = await self._get_catalog(catalog_id)

        if catalog.payment_model != "invoice_after_close":
            raise ValidationError(
                f"Catalog payment_model is '{catalog.payment_model}', "
                "expected 'invoice_after_close'"
            )

        now = datetime.now(timezone.utc)
        if catalog.buying_window_closes_at is None:
            raise ValidationError("Catalog has no buying_window_closes_at set")
        if catalog.buying_window_closes_at > now:
            raise ValidationError(
                "Buying window has not closed yet. "
                f"Closes at: {catalog.buying_window_closes_at.isoformat()}"
            )

        # Gather all orders for this catalog (any non-cancelled status)
        result = await self.db.execute(
            select(Order).where(
                Order.catalog_id == catalog_id,
                Order.status != "cancelled",
            )
        )
        orders = result.scalars().all()

        if not orders:
            raise ValidationError("No orders found for this catalog")

        company = await self._get_company(catalog.company_id)
        stripe_customer_id = await self._ensure_stripe_customer(company)

        # Gather all line items across all orders
        line_items_data: list[dict] = []
        total = Decimal("0")

        for order in orders:
            items = await self._get_order_line_items(order.id)
            for item in items:
                line_items_data.append({
                    "description": f"{item.product_name} ({item.product_sku}) x{item.quantity}",
                    "quantity": item.quantity,
                    "unit_amount_cents": int(item.unit_price * 100),
                })
                total += item.line_total

        # Create Stripe invoice
        metadata = {
            "reel48_company_id": str(catalog.company_id),
            "reel48_created_by": str(created_by),
            "reel48_catalog_id": str(catalog_id),
            "billing_flow": "post_window",
        }
        if catalog.sub_brand_id:
            metadata["reel48_sub_brand_id"] = str(catalog.sub_brand_id)

        stripe_invoice = await self._stripe.create_invoice(
            customer_id=stripe_customer_id,
            metadata=metadata,
            auto_advance=False,
        )

        for li in line_items_data:
            await self._stripe.create_invoice_item(
                customer_id=stripe_customer_id,
                invoice_id=stripe_invoice["id"],
                description=li["description"],
                quantity=li["quantity"],
                unit_amount_cents=li["unit_amount_cents"],
            )

        invoice = Invoice(
            company_id=catalog.company_id,
            sub_brand_id=catalog.sub_brand_id,
            catalog_id=catalog_id,
            stripe_invoice_id=stripe_invoice["id"],
            stripe_invoice_url=stripe_invoice.get("hosted_invoice_url"),
            billing_flow="post_window",
            status="draft",
            total_amount=total,
            buying_window_closes_at=catalog.buying_window_closes_at,
            created_by=created_by,
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info(
            "invoice_created",
            invoice_id=str(invoice.id),
            billing_flow="post_window",
            catalog_id=str(catalog_id),
            total_amount=str(total),
            order_count=len(orders),
        )
        return invoice

    async def create_self_service_invoice(
        self,
        order: Order,
        line_items: list[OrderLineItem],
    ) -> Invoice:
        """Flow 2: Auto-generate an invoice at checkout for a self-service catalog.

        Called during order placement (OrderService.create_order) when the catalog
        has payment_model = 'self_service'.
        - Looks up the company's stripe_customer_id
        - Creates and auto-finalizes a Stripe Invoice
        - Creates the local Invoice record with billing_flow = 'self_service'
        - NOTE: auto_advance=True for self-service (immediate billing)
        """
        company = await self._get_company(order.company_id)
        stripe_customer_id = await self._ensure_stripe_customer(company)

        metadata = {
            "reel48_company_id": str(order.company_id),
            "reel48_order_id": str(order.id),
            "billing_flow": "self_service",
        }
        if order.sub_brand_id:
            metadata["reel48_sub_brand_id"] = str(order.sub_brand_id)

        stripe_invoice = await self._stripe.create_invoice(
            customer_id=stripe_customer_id,
            metadata=metadata,
            auto_advance=True,  # Self-service: immediate billing
        )

        for item in line_items:
            await self._stripe.create_invoice_item(
                customer_id=stripe_customer_id,
                invoice_id=stripe_invoice["id"],
                description=f"{item.product_name} ({item.product_sku}) x{item.quantity}",
                quantity=item.quantity,
                unit_amount_cents=int(item.unit_price * 100),
            )

        invoice = Invoice(
            company_id=order.company_id,
            sub_brand_id=order.sub_brand_id,
            order_id=order.id,
            catalog_id=order.catalog_id,
            stripe_invoice_id=stripe_invoice["id"],
            stripe_invoice_url=stripe_invoice.get("hosted_invoice_url"),
            billing_flow="self_service",
            status="draft",
            total_amount=order.total_amount,
            created_by=order.user_id,
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info(
            "invoice_created",
            invoice_id=str(invoice.id),
            billing_flow="self_service",
            order_id=str(order.id),
            total_amount=str(order.total_amount),
        )
        return invoice

    async def link_invoice(
        self,
        stripe_invoice_id: str,
        company_id: UUID,
        created_by: UUID,
        sub_brand_id: UUID | None = None,
    ) -> Invoice:
        """Link an existing Stripe invoice to a client company.

        Fetches invoice details from Stripe and creates a local record.
        Supports historical invoices (any Stripe status — draft, open, paid, void, etc.).
        Webhooks will keep the status updated going forward.
        """
        # 1. Check for duplicate
        existing = await self._find_invoice_by_stripe_id(stripe_invoice_id)
        if existing is not None:
            raise ConflictError(
                f"An invoice with Stripe ID '{stripe_invoice_id}' already exists"
            )

        # 2. Validate company
        company = await self._get_company(company_id)

        # 3. Validate sub-brand belongs to company (if provided)
        if sub_brand_id is not None:
            result = await self.db.execute(
                select(SubBrand).where(
                    SubBrand.id == sub_brand_id,
                    SubBrand.company_id == company_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise ValidationError(
                    "Sub-brand does not exist or does not belong to the specified company"
                )

        # 4. Fetch from Stripe
        stripe_data = await self._stripe.get_invoice(stripe_invoice_id)

        # 5. Map Stripe status to local status
        stripe_status = stripe_data.get("status", "draft")
        status = self._map_stripe_status(stripe_status)

        # 6. Extract amounts (Stripe uses cents)
        raw_total = stripe_data.get("total") or stripe_data.get("amount_due") or 0
        total_amount = Decimal(raw_total) / Decimal(100)
        currency = stripe_data.get("currency", "usd")

        # 7. Extract due_date (Stripe sends Unix timestamp or None)
        raw_due_date = stripe_data.get("due_date")
        due_date = (
            datetime.fromtimestamp(raw_due_date, tz=timezone.utc).date()
            if raw_due_date
            else None
        )

        # 8. Extract paid_at from status_transitions
        paid_at = None
        if status == "paid":
            transitions = stripe_data.get("status_transitions") or {}
            raw_paid_at = transitions.get("paid_at")
            if raw_paid_at:
                paid_at = datetime.fromtimestamp(raw_paid_at, tz=timezone.utc)
            else:
                paid_at = datetime.now(timezone.utc)

        # 9. Create local record
        invoice = Invoice(
            company_id=company.id,
            sub_brand_id=sub_brand_id,
            stripe_invoice_id=stripe_invoice_id,
            stripe_invoice_url=stripe_data.get("hosted_invoice_url"),
            stripe_pdf_url=stripe_data.get("invoice_pdf"),
            invoice_number=stripe_data.get("number"),
            billing_flow="linked",
            status=status,
            total_amount=total_amount,
            currency=currency,
            due_date=due_date,
            created_by=created_by,
            paid_at=paid_at,
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info(
            "invoice_linked",
            invoice_id=str(invoice.id),
            stripe_invoice_id=stripe_invoice_id,
            company_id=str(company_id),
            status=status,
            total_amount=str(total_amount),
        )
        return invoice

    @staticmethod
    def _map_stripe_status(stripe_status: str) -> str:
        """Map Stripe invoice status to local status."""
        mapping = {
            "draft": "draft",
            "open": "sent",
            "paid": "paid",
            "void": "voided",
            "uncollectible": "payment_failed",
        }
        return mapping.get(stripe_status, "draft")

    async def finalize_invoice(self, invoice_id: UUID) -> Invoice:
        """Finalize a draft invoice. Stripe assigns an invoice number."""
        invoice = await self._get_invoice_by_id(invoice_id)

        if invoice.status != "draft":
            raise ForbiddenError(
                f"Cannot finalize invoice in '{invoice.status}' status (must be 'draft')"
            )

        stripe_result = await self._stripe.finalize_invoice(invoice.stripe_invoice_id)

        invoice.status = "finalized"
        invoice.invoice_number = stripe_result.get("number")
        invoice.stripe_invoice_url = stripe_result.get("hosted_invoice_url")
        invoice.stripe_pdf_url = stripe_result.get("invoice_pdf")

        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info(
            "invoice_finalized",
            invoice_id=str(invoice_id),
            invoice_number=invoice.invoice_number,
        )
        return invoice

    async def send_invoice(self, invoice_id: UUID) -> Invoice:
        """Send a finalized invoice to the client company."""
        invoice = await self._get_invoice_by_id(invoice_id)

        if invoice.status != "finalized":
            raise ForbiddenError(
                f"Cannot send invoice in '{invoice.status}' status (must be 'finalized')"
            )

        await self._stripe.send_invoice(invoice.stripe_invoice_id)

        invoice.status = "sent"
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info("invoice_sent", invoice_id=str(invoice_id))
        return invoice

    async def void_invoice(self, invoice_id: UUID) -> Invoice:
        """Void an invoice (only draft or finalized, not paid)."""
        invoice = await self._get_invoice_by_id(invoice_id)

        if invoice.status not in ("draft", "finalized", "sent"):
            raise ForbiddenError(
                f"Cannot void invoice in '{invoice.status}' status "
                "(must be 'draft', 'finalized', or 'sent')"
            )

        await self._stripe.void_invoice(invoice.stripe_invoice_id)

        invoice.status = "voided"
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info("invoice_voided", invoice_id=str(invoice_id))
        return invoice

    # ═══════════════════════════════════════════════════════════════════════
    # Webhook Handlers
    # ═══════════════════════════════════════════════════════════════════════

    async def handle_webhook_event(self, event: dict) -> None:
        """Dispatch webhook events to specific handlers.

        Process idempotently — check current status before updating.
        """
        event_type = event.get("type", "")
        stripe_invoice = event.get("data", {}).get("object", {})

        handlers = {
            "invoice.finalized": self.handle_invoice_finalized,
            "invoice.sent": self.handle_invoice_sent,
            "invoice.paid": self.handle_invoice_paid,
            "invoice.payment_failed": self.handle_payment_failed,
            "invoice.voided": self.handle_invoice_voided,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(stripe_invoice)
        else:
            logger.info("webhook_event_ignored", event_type=event_type)

    async def handle_invoice_finalized(self, stripe_invoice: dict) -> None:
        """Update local status to 'finalized', store invoice_number."""
        invoice = await self._find_invoice_by_stripe_id(stripe_invoice.get("id", ""))
        if invoice is None:
            logger.warning(
                "webhook_invoice_not_found",
                stripe_invoice_id=stripe_invoice.get("id"),
            )
            return

        # Idempotency: don't regress status
        if _STATUS_ORDER.get(invoice.status, 0) >= _STATUS_ORDER.get("finalized", 0):
            logger.info(
                "webhook_skipped_idempotent",
                invoice_id=str(invoice.id),
                current_status=invoice.status,
                event_status="finalized",
            )
            return

        invoice.status = "finalized"
        invoice.invoice_number = stripe_invoice.get("number")
        invoice.stripe_invoice_url = stripe_invoice.get("hosted_invoice_url")
        invoice.stripe_pdf_url = stripe_invoice.get("invoice_pdf")
        await self.db.flush()

        logger.info(
            "webhook_invoice_finalized",
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
        )

    async def handle_invoice_sent(self, stripe_invoice: dict) -> None:
        """Update local status to 'sent'."""
        invoice = await self._find_invoice_by_stripe_id(stripe_invoice.get("id", ""))
        if invoice is None:
            return

        if _STATUS_ORDER.get(invoice.status, 0) >= _STATUS_ORDER.get("sent", 0):
            return

        invoice.status = "sent"
        await self.db.flush()
        logger.info("webhook_invoice_sent", invoice_id=str(invoice.id))

    async def handle_invoice_paid(self, stripe_invoice: dict) -> None:
        """Update local status to 'paid', record paid_at timestamp."""
        invoice = await self._find_invoice_by_stripe_id(stripe_invoice.get("id", ""))
        if invoice is None:
            return

        if invoice.status == "paid":
            return  # Already paid — idempotent

        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("webhook_invoice_paid", invoice_id=str(invoice.id))

    async def handle_payment_failed(self, stripe_invoice: dict) -> None:
        """Update local status to 'payment_failed'."""
        invoice = await self._find_invoice_by_stripe_id(stripe_invoice.get("id", ""))
        if invoice is None:
            return

        if invoice.status == "paid":
            return  # Don't overwrite paid status

        invoice.status = "payment_failed"
        await self.db.flush()
        logger.info("webhook_payment_failed", invoice_id=str(invoice.id))

    async def handle_invoice_voided(self, stripe_invoice: dict) -> None:
        """Update local status to 'voided'."""
        invoice = await self._find_invoice_by_stripe_id(stripe_invoice.get("id", ""))
        if invoice is None:
            return

        if invoice.status == "voided":
            return  # Already voided — idempotent

        invoice.status = "voided"
        await self.db.flush()
        logger.info("webhook_invoice_voided", invoice_id=str(invoice.id))

    # ═══════════════════════════════════════════════════════════════════════
    # Client-Facing Queries (tenant-scoped)
    # ═══════════════════════════════════════════════════════════════════════

    async def list_invoices(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
        status: str | None = None,
        billing_flow: str | None = None,
    ) -> tuple[list[Invoice], int]:
        """List invoices with tenant scoping and optional filters."""
        query = select(Invoice).where(Invoice.company_id == company_id)

        if sub_brand_id is not None:
            query = query.where(Invoice.sub_brand_id == sub_brand_id)
        if status:
            query = query.where(Invoice.status == status)
        if billing_flow:
            query = query.where(Invoice.billing_flow == billing_flow)

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginated results
        query = (
            query.order_by(Invoice.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_invoice(
        self,
        invoice_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> Invoice:
        """Get a single invoice by ID with tenant scoping."""
        query = select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
        )
        if sub_brand_id is not None:
            query = query.where(Invoice.sub_brand_id == sub_brand_id)

        result = await self.db.execute(query)
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice", str(invoice_id))
        return invoice

    # ═══════════════════════════════════════════════════════════════════════
    # Platform Admin Queries (reel48_admin, cross-company)
    # ═══════════════════════════════════════════════════════════════════════

    async def list_all_invoices(
        self,
        company_id: UUID | None = None,
        status: str | None = None,
        billing_flow: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Invoice], int]:
        """Cross-company invoice list for reel48_admin. Optional filters."""
        query = select(Invoice)

        if company_id is not None:
            query = query.where(Invoice.company_id == company_id)
        if status:
            query = query.where(Invoice.status == status)
        if billing_flow:
            query = query.where(Invoice.billing_flow == billing_flow)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = (
            query.order_by(Invoice.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_invoice_by_id(self, invoice_id: UUID) -> Invoice:
        """Get a single invoice by ID without tenant scoping (platform admin)."""
        return await self._get_invoice_by_id(invoice_id)

    # ═══════════════════════════════════════════════════════════════════════
    # Private Helpers
    # ═══════════════════════════════════════════════════════════════════════

    async def _get_company(self, company_id: UUID) -> Company:
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if company is None:
            raise NotFoundError("Company", str(company_id))
        return company

    async def _ensure_stripe_customer(self, company: Company) -> str:
        """Get or create a Stripe Customer for the company, updating the DB if needed."""
        stripe_customer_id = await self._stripe.get_or_create_customer(
            company_id=str(company.id),
            company_name=company.name,
            stripe_customer_id=company.stripe_customer_id,
        )
        if company.stripe_customer_id != stripe_customer_id:
            company.stripe_customer_id = stripe_customer_id
            await self.db.flush()
        return stripe_customer_id

    async def _get_order(self, order_id: UUID, company_id: UUID) -> Order:
        result = await self.db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.company_id == company_id,
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise NotFoundError("Order", str(order_id))
        return order

    async def _get_order_line_items(self, order_id: UUID) -> list[OrderLineItem]:
        result = await self.db.execute(
            select(OrderLineItem).where(OrderLineItem.order_id == order_id)
        )
        return list(result.scalars().all())

    async def _get_bulk_order(self, bulk_order_id: UUID, company_id: UUID) -> BulkOrder:
        result = await self.db.execute(
            select(BulkOrder).where(
                BulkOrder.id == bulk_order_id,
                BulkOrder.company_id == company_id,
            )
        )
        bulk_order = result.scalar_one_or_none()
        if bulk_order is None:
            raise NotFoundError("BulkOrder", str(bulk_order_id))
        return bulk_order

    async def _get_bulk_order_items(self, bulk_order_id: UUID) -> list[BulkOrderItem]:
        result = await self.db.execute(
            select(BulkOrderItem).where(BulkOrderItem.bulk_order_id == bulk_order_id)
        )
        return list(result.scalars().all())

    async def _get_catalog(self, catalog_id: UUID) -> Catalog:
        result = await self.db.execute(
            select(Catalog).where(Catalog.id == catalog_id)
        )
        catalog = result.scalar_one_or_none()
        if catalog is None:
            raise NotFoundError("Catalog", str(catalog_id))
        return catalog

    async def _get_invoice_by_id(self, invoice_id: UUID) -> Invoice:
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice", str(invoice_id))
        return invoice

    async def _find_invoice_by_stripe_id(self, stripe_invoice_id: str) -> Invoice | None:
        """Look up a local invoice by Stripe invoice ID. Returns None if not found."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
        )
        return result.scalar_one_or_none()
