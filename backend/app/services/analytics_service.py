from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest
from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.models.company import Company
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.product import Product
from app.models.sub_brand import SubBrand
from app.models.user import User

logger = structlog.get_logger()

# Statuses that represent "completed" spend (not pending/cancelled)
_SPEND_STATUSES = ("approved", "processing", "shipped", "delivered")


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _apply_date_range(self, query, date_column, start_date: date | None, end_date: date | None):
        """Applies optional date range filtering to a SQLAlchemy query."""
        if start_date:
            query = query.where(date_column >= start_date)
        if end_date:
            query = query.where(date_column <= end_date)
        return query

    # ------------------------------------------------------------------
    # Spend Analytics
    # ------------------------------------------------------------------
    async def get_spend_summary(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        """
        Returns total spend, order count, average order value.
        Only counts orders with status in ('approved', 'processing', 'shipped', 'delivered').
        """
        # Individual orders
        ind_query = select(
            func.coalesce(func.sum(Order.total_amount), Decimal(0)).label("total"),
            func.count(Order.id).label("count"),
        ).where(Order.status.in_(_SPEND_STATUSES))
        ind_query = self._apply_date_range(ind_query, Order.created_at, start_date, end_date)
        ind_result = (await self.db.execute(ind_query)).one()

        # Bulk orders
        bulk_query = select(
            func.coalesce(func.sum(BulkOrder.total_amount), Decimal(0)).label("total"),
            func.count(BulkOrder.id).label("count"),
        ).where(BulkOrder.status.in_(_SPEND_STATUSES))
        bulk_query = self._apply_date_range(bulk_query, BulkOrder.created_at, start_date, end_date)
        bulk_result = (await self.db.execute(bulk_query)).one()

        individual_spend = ind_result.total or Decimal(0)
        bulk_spend = bulk_result.total or Decimal(0)
        total_spend = individual_spend + bulk_spend
        order_count = ind_result.count + bulk_result.count
        avg_order_value = total_spend / order_count if order_count > 0 else Decimal(0)

        return {
            "total_spend": total_spend,
            "order_count": order_count,
            "average_order_value": avg_order_value,
            "individual_order_spend": individual_spend,
            "bulk_order_spend": bulk_spend,
        }

    async def get_spend_by_sub_brand(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """Spend broken down by sub-brand. Joins orders → sub_brands for name."""
        # Individual orders by sub-brand
        ind_query = (
            select(
                Order.sub_brand_id,
                SubBrand.name.label("sub_brand_name"),
                func.coalesce(func.sum(Order.total_amount), Decimal(0)).label("total_spend"),
                func.count(Order.id).label("order_count"),
            )
            .join(SubBrand, SubBrand.id == Order.sub_brand_id)
            .where(Order.status.in_(_SPEND_STATUSES))
            .group_by(Order.sub_brand_id, SubBrand.name)
        )
        ind_query = self._apply_date_range(ind_query, Order.created_at, start_date, end_date)

        # Bulk orders by sub-brand
        bulk_query = (
            select(
                BulkOrder.sub_brand_id,
                SubBrand.name.label("sub_brand_name"),
                func.coalesce(func.sum(BulkOrder.total_amount), Decimal(0)).label("total_spend"),
                func.count(BulkOrder.id).label("order_count"),
            )
            .join(SubBrand, SubBrand.id == BulkOrder.sub_brand_id)
            .where(BulkOrder.status.in_(_SPEND_STATUSES))
            .group_by(BulkOrder.sub_brand_id, SubBrand.name)
        )
        bulk_query = self._apply_date_range(bulk_query, BulkOrder.created_at, start_date, end_date)

        ind_rows = (await self.db.execute(ind_query)).all()
        bulk_rows = (await self.db.execute(bulk_query)).all()

        # Merge individual + bulk by sub_brand_id
        merged: dict[UUID, dict] = {}
        for row in ind_rows:
            merged[row.sub_brand_id] = {
                "sub_brand_id": row.sub_brand_id,
                "sub_brand_name": row.sub_brand_name,
                "total_spend": row.total_spend,
                "order_count": row.order_count,
            }
        for row in bulk_rows:
            if row.sub_brand_id in merged:
                merged[row.sub_brand_id]["total_spend"] += row.total_spend
                merged[row.sub_brand_id]["order_count"] += row.order_count
            else:
                merged[row.sub_brand_id] = {
                    "sub_brand_id": row.sub_brand_id,
                    "sub_brand_name": row.sub_brand_name,
                    "total_spend": row.total_spend,
                    "order_count": row.order_count,
                }

        return list(merged.values())

    async def get_spend_over_time(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "month",
    ) -> list[dict]:
        """Spend aggregated into time buckets for trend charting."""
        if granularity not in ("day", "week", "month"):
            granularity = "month"

        # Individual orders
        ind_query = (
            select(
                func.date_trunc(granularity, Order.created_at).label("period"),
                func.coalesce(func.sum(Order.total_amount), Decimal(0)).label("total_spend"),
                func.count(Order.id).label("order_count"),
            )
            .where(Order.status.in_(_SPEND_STATUSES))
            .group_by(text("1"))
        )
        ind_query = self._apply_date_range(ind_query, Order.created_at, start_date, end_date)

        # Bulk orders
        bulk_query = (
            select(
                func.date_trunc(granularity, BulkOrder.created_at).label("period"),
                func.coalesce(func.sum(BulkOrder.total_amount), Decimal(0)).label("total_spend"),
                func.count(BulkOrder.id).label("order_count"),
            )
            .where(BulkOrder.status.in_(_SPEND_STATUSES))
            .group_by(text("1"))
        )
        bulk_query = self._apply_date_range(bulk_query, BulkOrder.created_at, start_date, end_date)

        ind_rows = (await self.db.execute(ind_query)).all()
        bulk_rows = (await self.db.execute(bulk_query)).all()

        # Merge by period
        merged: dict[str, dict] = {}
        for row in ind_rows:
            period_str = row.period.isoformat() if row.period else "unknown"
            merged[period_str] = {
                "period": period_str,
                "total_spend": row.total_spend,
                "order_count": row.order_count,
            }
        for row in bulk_rows:
            period_str = row.period.isoformat() if row.period else "unknown"
            if period_str in merged:
                merged[period_str]["total_spend"] += row.total_spend
                merged[period_str]["order_count"] += row.order_count
            else:
                merged[period_str] = {
                    "period": period_str,
                    "total_spend": row.total_spend,
                    "order_count": row.order_count,
                }

        return sorted(merged.values(), key=lambda x: x["period"])

    # ------------------------------------------------------------------
    # Order Analytics
    # ------------------------------------------------------------------
    async def get_order_status_breakdown(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """Count of orders by status, separated by order type."""
        # Individual orders
        ind_query = (
            select(
                Order.status,
                func.count(Order.id).label("count"),
            )
            .group_by(Order.status)
        )
        ind_query = self._apply_date_range(ind_query, Order.created_at, start_date, end_date)

        # Bulk orders
        bulk_query = (
            select(
                BulkOrder.status,
                func.count(BulkOrder.id).label("count"),
            )
            .group_by(BulkOrder.status)
        )
        bulk_query = self._apply_date_range(bulk_query, BulkOrder.created_at, start_date, end_date)

        ind_rows = (await self.db.execute(ind_query)).all()
        bulk_rows = (await self.db.execute(bulk_query)).all()

        results = []
        for row in ind_rows:
            results.append({"status": row.status, "count": row.count, "order_type": "individual"})
        for row in bulk_rows:
            results.append({"status": row.status, "count": row.count, "order_type": "bulk"})

        return results

    async def get_top_products(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Most ordered products by quantity across individual and bulk orders."""
        # Individual line items
        ind_query = (
            select(
                OrderLineItem.product_id,
                OrderLineItem.product_name,
                OrderLineItem.product_sku,
                func.sum(OrderLineItem.quantity).label("total_quantity"),
                func.sum(OrderLineItem.line_total).label("total_revenue"),
            )
            .group_by(
                OrderLineItem.product_id,
                OrderLineItem.product_name,
                OrderLineItem.product_sku,
            )
        )
        ind_query = self._apply_date_range(ind_query, OrderLineItem.created_at, start_date, end_date)

        # Bulk order items
        bulk_query = (
            select(
                BulkOrderItem.product_id,
                BulkOrderItem.product_name,
                BulkOrderItem.product_sku,
                func.sum(BulkOrderItem.quantity).label("total_quantity"),
                func.sum(BulkOrderItem.line_total).label("total_revenue"),
            )
            .group_by(
                BulkOrderItem.product_id,
                BulkOrderItem.product_name,
                BulkOrderItem.product_sku,
            )
        )
        bulk_query = self._apply_date_range(bulk_query, BulkOrderItem.created_at, start_date, end_date)

        ind_rows = (await self.db.execute(ind_query)).all()
        bulk_rows = (await self.db.execute(bulk_query)).all()

        # Merge by product_id
        merged: dict[UUID, dict] = {}
        for row in ind_rows:
            merged[row.product_id] = {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_sku": row.product_sku,
                "total_quantity": int(row.total_quantity),
                "total_revenue": row.total_revenue,
            }
        for row in bulk_rows:
            if row.product_id in merged:
                merged[row.product_id]["total_quantity"] += int(row.total_quantity)
                merged[row.product_id]["total_revenue"] += row.total_revenue
            else:
                merged[row.product_id] = {
                    "product_id": row.product_id,
                    "product_name": row.product_name,
                    "product_sku": row.product_sku,
                    "total_quantity": int(row.total_quantity),
                    "total_revenue": row.total_revenue,
                }

        # Sort by total_quantity descending, take top N
        sorted_products = sorted(merged.values(), key=lambda x: x["total_quantity"], reverse=True)
        return sorted_products[:limit]

    # ------------------------------------------------------------------
    # Size Distribution Analytics
    # ------------------------------------------------------------------
    async def get_size_distribution(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """Distribution of ordered sizes across all line items."""
        # Individual line items (exclude NULL sizes)
        ind_query = (
            select(
                OrderLineItem.size,
                func.sum(OrderLineItem.quantity).label("count"),
            )
            .where(OrderLineItem.size.isnot(None))
            .group_by(OrderLineItem.size)
        )
        ind_query = self._apply_date_range(ind_query, OrderLineItem.created_at, start_date, end_date)

        # Bulk order items
        bulk_query = (
            select(
                BulkOrderItem.size,
                func.sum(BulkOrderItem.quantity).label("count"),
            )
            .where(BulkOrderItem.size.isnot(None))
            .group_by(BulkOrderItem.size)
        )
        bulk_query = self._apply_date_range(bulk_query, BulkOrderItem.created_at, start_date, end_date)

        ind_rows = (await self.db.execute(ind_query)).all()
        bulk_rows = (await self.db.execute(bulk_query)).all()

        # Merge
        merged: dict[str, int] = {}
        for row in ind_rows:
            merged[row.size] = merged.get(row.size, 0) + int(row.count)
        for row in bulk_rows:
            merged[row.size] = merged.get(row.size, 0) + int(row.count)

        total = sum(merged.values())
        results = []
        for size_name, count in sorted(merged.items()):
            results.append({
                "size": size_name,
                "count": count,
                "percentage": round(count / total * 100, 2) if total > 0 else 0.0,
            })

        return results

    # ------------------------------------------------------------------
    # Invoice Analytics
    # ------------------------------------------------------------------
    async def get_invoice_summary(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        """Invoice totals by status and billing flow."""
        base_query = select(Invoice)
        base_query = self._apply_date_range(base_query, Invoice.created_at, start_date, end_date)

        # Total invoiced (all non-voided)
        total_query = select(
            func.coalesce(func.sum(Invoice.total_amount), Decimal(0)),
        ).where(Invoice.status != "voided")
        total_query = self._apply_date_range(total_query, Invoice.created_at, start_date, end_date)
        total_invoiced = (await self.db.execute(total_query)).scalar() or Decimal(0)

        # Total paid
        paid_query = select(
            func.coalesce(func.sum(Invoice.total_amount), Decimal(0)),
        ).where(Invoice.status == "paid")
        paid_query = self._apply_date_range(paid_query, Invoice.created_at, start_date, end_date)
        total_paid = (await self.db.execute(paid_query)).scalar() or Decimal(0)

        # Total outstanding (finalized + sent, not paid/voided)
        outstanding_query = select(
            func.coalesce(func.sum(Invoice.total_amount), Decimal(0)),
        ).where(Invoice.status.in_(("finalized", "sent")))
        outstanding_query = self._apply_date_range(outstanding_query, Invoice.created_at, start_date, end_date)
        total_outstanding = (await self.db.execute(outstanding_query)).scalar() or Decimal(0)

        # Count
        count_query = select(func.count(Invoice.id))
        count_query = self._apply_date_range(count_query, Invoice.created_at, start_date, end_date)
        invoice_count = (await self.db.execute(count_query)).scalar() or 0

        # By status
        status_query = (
            select(
                Invoice.status,
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal(0)).label("total"),
            )
            .group_by(Invoice.status)
        )
        status_query = self._apply_date_range(status_query, Invoice.created_at, start_date, end_date)
        status_rows = (await self.db.execute(status_query)).all()

        # By billing flow
        flow_query = (
            select(
                Invoice.billing_flow,
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal(0)).label("total"),
            )
            .group_by(Invoice.billing_flow)
        )
        flow_query = self._apply_date_range(flow_query, Invoice.created_at, start_date, end_date)
        flow_rows = (await self.db.execute(flow_query)).all()

        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "invoice_count": invoice_count,
            "by_status": [
                {"status": r.status, "count": r.count, "total": r.total}
                for r in status_rows
            ],
            "by_billing_flow": [
                {"billing_flow": r.billing_flow, "count": r.count, "total": r.total}
                for r in flow_rows
            ],
        }

    # ------------------------------------------------------------------
    # Approval Analytics
    # ------------------------------------------------------------------
    async def get_approval_metrics(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        """Approval request metrics: pending count, average approval time, approval rate."""
        base_where = []

        # Count by status
        pending_query = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.status == "pending"
        )
        pending_query = self._apply_date_range(pending_query, ApprovalRequest.requested_at, start_date, end_date)
        pending_count = (await self.db.execute(pending_query)).scalar() or 0

        approved_query = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.status == "approved"
        )
        approved_query = self._apply_date_range(approved_query, ApprovalRequest.requested_at, start_date, end_date)
        approved_count = (await self.db.execute(approved_query)).scalar() or 0

        rejected_query = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.status == "rejected"
        )
        rejected_query = self._apply_date_range(rejected_query, ApprovalRequest.requested_at, start_date, end_date)
        rejected_count = (await self.db.execute(rejected_query)).scalar() or 0

        decided_total = approved_count + rejected_count
        approval_rate = approved_count / decided_total if decided_total > 0 else 0.0

        # Average approval time (decided_at - requested_at) for decided requests
        avg_time_query = select(
            func.avg(
                func.extract("epoch", ApprovalRequest.decided_at)
                - func.extract("epoch", ApprovalRequest.requested_at)
            )
        ).where(
            ApprovalRequest.decided_at.isnot(None)
        )
        avg_time_query = self._apply_date_range(avg_time_query, ApprovalRequest.requested_at, start_date, end_date)
        avg_seconds = (await self.db.execute(avg_time_query)).scalar()
        avg_approval_time_hours = round(float(avg_seconds) / 3600, 2) if avg_seconds is not None else None

        return {
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "approval_rate": round(approval_rate, 4),
            "avg_approval_time_hours": avg_approval_time_hours,
        }

    # ------------------------------------------------------------------
    # Platform-Level Analytics (reel48_admin only)
    # ------------------------------------------------------------------
    async def get_platform_overview(self) -> dict:
        """
        Cross-company platform metrics. Called when RLS session vars are set to
        empty string (reel48_admin context), so all companies are visible.
        """
        total_companies = (await self.db.execute(
            select(func.count(Company.id)).where(Company.is_active.is_(True))
        )).scalar() or 0

        total_sub_brands = (await self.db.execute(
            select(func.count(SubBrand.id)).where(SubBrand.is_active.is_(True))
        )).scalar() or 0

        total_users = (await self.db.execute(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )).scalar() or 0

        total_orders = (await self.db.execute(
            select(func.count(Order.id))
        )).scalar() or 0

        total_revenue = (await self.db.execute(
            select(func.coalesce(func.sum(Invoice.total_amount), Decimal(0))).where(
                Invoice.status == "paid"
            )
        )).scalar() or Decimal(0)

        active_catalogs = (await self.db.execute(
            select(func.count(Catalog.id)).where(Catalog.status == "active")
        )).scalar() or 0

        return {
            "total_companies": total_companies,
            "total_sub_brands": total_sub_brands,
            "total_users": total_users,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "active_catalogs": active_catalogs,
        }

    async def get_revenue_by_company(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict]:
        """Revenue breakdown by company (from paid invoices)."""
        query = (
            select(
                Invoice.company_id,
                Company.name.label("company_name"),
                func.coalesce(func.sum(Invoice.total_amount), Decimal(0)).label("total_revenue"),
                func.count(Invoice.id).label("invoice_count"),
            )
            .join(Company, Company.id == Invoice.company_id)
            .where(Invoice.status == "paid")
            .group_by(Invoice.company_id, Company.name)
        )
        query = self._apply_date_range(query, Invoice.created_at, start_date, end_date)

        rows = (await self.db.execute(query)).all()
        return [
            {
                "company_id": row.company_id,
                "company_name": row.company_name,
                "total_revenue": row.total_revenue,
                "invoice_count": row.invoice_count,
            }
            for row in rows
        ]
