"""
Tests for AnalyticsService — Module 8 Phase 1.

Tests verify aggregation correctness, date filtering, and tenant isolation.
Functional tests use admin_db_session (superuser, RLS bypassed).
Isolation tests use db_session (reel48_app role, RLS enforced).
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
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
from app.services.analytics_service import AnalyticsService


# ---------------------------------------------------------------------------
# Helper factories — create test data directly in the database
# ---------------------------------------------------------------------------
def _make_catalog(company_id, sub_brand_id, created_by, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name="Test Catalog",
        slug=f"cat-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="active",
        created_by=created_by,
    )
    defaults.update(overrides)
    return Catalog(**defaults)


def _make_product(company_id, sub_brand_id, created_by, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name="Test Product",
        sku=f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=Decimal("25.00"),
        status="active",
        created_by=created_by,
    )
    defaults.update(overrides)
    return Product(**defaults)


def _make_order(company_id, sub_brand_id, user_id, catalog_id, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user_id,
        catalog_id=catalog_id,
        order_number=f"ORD-{uuid4().hex[:8].upper()}",
        status="approved",
        subtotal=Decimal("100.00"),
        total_amount=Decimal("100.00"),
    )
    defaults.update(overrides)
    return Order(**defaults)


def _make_line_item(company_id, sub_brand_id, order_id, product_id, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        order_id=order_id,
        product_id=product_id,
        product_name="Test Product",
        product_sku="SKU-TEST",
        unit_price=Decimal("25.00"),
        quantity=2,
        size="M",
        line_total=Decimal("50.00"),
    )
    defaults.update(overrides)
    return OrderLineItem(**defaults)


def _make_bulk_order(company_id, sub_brand_id, catalog_id, created_by, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        catalog_id=catalog_id,
        created_by=created_by,
        title="Test Bulk Order",
        order_number=f"BLK-{uuid4().hex[:8].upper()}",
        status="approved",
        total_items=5,
        total_amount=Decimal("200.00"),
    )
    defaults.update(overrides)
    return BulkOrder(**defaults)


def _make_bulk_item(company_id, sub_brand_id, bulk_order_id, product_id, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        bulk_order_id=bulk_order_id,
        product_id=product_id,
        product_name="Bulk Product",
        product_sku="SKU-BULK",
        unit_price=Decimal("40.00"),
        quantity=5,
        size="L",
        line_total=Decimal("200.00"),
    )
    defaults.update(overrides)
    return BulkOrderItem(**defaults)


def _make_invoice(company_id, sub_brand_id, created_by, **overrides):
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        stripe_invoice_id=f"in_test_{uuid4().hex[:8]}",
        billing_flow="assigned",
        status="paid",
        total_amount=Decimal("500.00"),
        currency="usd",
        created_by=created_by,
    )
    defaults.update(overrides)
    return Invoice(**defaults)


def _make_approval(company_id, sub_brand_id, requested_by, **overrides):
    now = datetime.now(UTC)
    defaults = dict(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        entity_type="order",
        entity_id=uuid4(),
        requested_by=requested_by,
        status="pending",
        requested_at=now,
    )
    defaults.update(overrides)
    return ApprovalRequest(**defaults)


# ---------------------------------------------------------------------------
# Fixtures — reusable analytics test data
# ---------------------------------------------------------------------------
@pytest.fixture
async def analytics_data(admin_db_session: AsyncSession, company_a, company_b):
    """
    Creates a rich set of test data across companies for analytics tests.
    Returns a dict of created entities for assertions.
    """
    comp_a, brand_a1, brand_a2 = company_a
    comp_b, brand_b1 = company_b

    # Users
    user_a1 = User(
        company_id=comp_a.id, sub_brand_id=brand_a1.id,
        cognito_sub=str(uuid4()), email=f"analytics-a1-{uuid4().hex[:6]}@a.com",
        full_name="Analytics User A1", role="employee",
    )
    user_a2 = User(
        company_id=comp_a.id, sub_brand_id=brand_a2.id,
        cognito_sub=str(uuid4()), email=f"analytics-a2-{uuid4().hex[:6]}@a.com",
        full_name="Analytics User A2", role="employee",
    )
    user_b1 = User(
        company_id=comp_b.id, sub_brand_id=brand_b1.id,
        cognito_sub=str(uuid4()), email=f"analytics-b1-{uuid4().hex[:6]}@b.com",
        full_name="Analytics User B1", role="employee",
    )
    admin_db_session.add_all([user_a1, user_a2, user_b1])
    await admin_db_session.flush()

    # Catalogs
    cat_a1 = _make_catalog(comp_a.id, brand_a1.id, user_a1.id)
    cat_a2 = _make_catalog(comp_a.id, brand_a2.id, user_a2.id)
    cat_b1 = _make_catalog(comp_b.id, brand_b1.id, user_b1.id)
    admin_db_session.add_all([cat_a1, cat_a2, cat_b1])
    await admin_db_session.flush()

    # Products
    prod_a1 = _make_product(comp_a.id, brand_a1.id, user_a1.id, name="Widget Alpha", sku="WA-001")
    prod_a2 = _make_product(comp_a.id, brand_a1.id, user_a1.id, name="Widget Beta", sku="WB-001")
    prod_b1 = _make_product(comp_b.id, brand_b1.id, user_b1.id, name="Gadget One", sku="G1-001")
    admin_db_session.add_all([prod_a1, prod_a2, prod_b1])
    await admin_db_session.flush()

    # Orders — Company A, Brand A1 (two approved orders)
    order_a1_1 = _make_order(comp_a.id, brand_a1.id, user_a1.id, cat_a1.id,
                             total_amount=Decimal("150.00"), subtotal=Decimal("150.00"))
    order_a1_2 = _make_order(comp_a.id, brand_a1.id, user_a1.id, cat_a1.id,
                             status="delivered", total_amount=Decimal("75.00"), subtotal=Decimal("75.00"))
    # Company A, Brand A2 (one approved order)
    order_a2_1 = _make_order(comp_a.id, brand_a2.id, user_a2.id, cat_a2.id,
                             total_amount=Decimal("200.00"), subtotal=Decimal("200.00"))
    # Cancelled order (should be excluded from spend)
    order_a1_cancelled = _make_order(comp_a.id, brand_a1.id, user_a1.id, cat_a1.id,
                                     status="cancelled", total_amount=Decimal("999.00"),
                                     subtotal=Decimal("999.00"))
    # Pending order (should be excluded from spend)
    order_a1_pending = _make_order(comp_a.id, brand_a1.id, user_a1.id, cat_a1.id,
                                   status="pending", total_amount=Decimal("50.00"),
                                   subtotal=Decimal("50.00"))
    # Company B order
    order_b1_1 = _make_order(comp_b.id, brand_b1.id, user_b1.id, cat_b1.id,
                             total_amount=Decimal("300.00"), subtotal=Decimal("300.00"))
    admin_db_session.add_all([order_a1_1, order_a1_2, order_a2_1, order_a1_cancelled,
                              order_a1_pending, order_b1_1])
    await admin_db_session.flush()

    # Line items — product_name/sku snapshot must match expectations
    li_a1_1 = _make_line_item(comp_a.id, brand_a1.id, order_a1_1.id, prod_a1.id,
                               product_name="Widget Alpha", product_sku="WA-001",
                               quantity=3, size="M", line_total=Decimal("75.00"))
    li_a1_2 = _make_line_item(comp_a.id, brand_a1.id, order_a1_1.id, prod_a2.id,
                               product_name="Widget Beta", product_sku="WB-001",
                               quantity=3, size="L", line_total=Decimal("75.00"))
    li_a1_3 = _make_line_item(comp_a.id, brand_a1.id, order_a1_2.id, prod_a1.id,
                               product_name="Widget Alpha", product_sku="WA-001",
                               quantity=1, size="S", line_total=Decimal("75.00"))
    li_a2_1 = _make_line_item(comp_a.id, brand_a2.id, order_a2_1.id, prod_a1.id,
                               product_name="Widget Alpha", product_sku="WA-001",
                               quantity=4, size="XL", line_total=Decimal("200.00"))
    li_b1_1 = _make_line_item(comp_b.id, brand_b1.id, order_b1_1.id, prod_b1.id,
                               product_name="Gadget One", product_sku="G1-001",
                               quantity=6, size="M", line_total=Decimal("300.00"))
    admin_db_session.add_all([li_a1_1, li_a1_2, li_a1_3, li_a2_1, li_b1_1])
    await admin_db_session.flush()

    # Bulk orders
    bulk_a1 = _make_bulk_order(comp_a.id, brand_a1.id, cat_a1.id, user_a1.id,
                               total_amount=Decimal("500.00"), total_items=10)
    bulk_b1 = _make_bulk_order(comp_b.id, brand_b1.id, cat_b1.id, user_b1.id,
                               total_amount=Decimal("400.00"), total_items=8)
    admin_db_session.add_all([bulk_a1, bulk_b1])
    await admin_db_session.flush()

    # Bulk order items
    bi_a1 = _make_bulk_item(comp_a.id, brand_a1.id, bulk_a1.id, prod_a1.id,
                             product_name="Widget Alpha", product_sku="WA-001",
                             quantity=10, size="L", line_total=Decimal("500.00"))
    bi_b1 = _make_bulk_item(comp_b.id, brand_b1.id, bulk_b1.id, prod_b1.id,
                             product_name="Gadget One", product_sku="G1-001",
                             quantity=8, size="XL", line_total=Decimal("400.00"))
    admin_db_session.add_all([bi_a1, bi_b1])
    await admin_db_session.flush()

    # Invoices
    inv_a1_paid = _make_invoice(comp_a.id, brand_a1.id, user_a1.id,
                                 status="paid", total_amount=Decimal("150.00"),
                                 billing_flow="assigned")
    inv_a1_sent = _make_invoice(comp_a.id, brand_a1.id, user_a1.id,
                                 status="sent", total_amount=Decimal("75.00"),
                                 billing_flow="self_service")
    inv_a2_finalized = _make_invoice(comp_a.id, brand_a2.id, user_a2.id,
                                      status="finalized", total_amount=Decimal("200.00"),
                                      billing_flow="post_window")
    inv_a1_voided = _make_invoice(comp_a.id, brand_a1.id, user_a1.id,
                                   status="voided", total_amount=Decimal("999.00"),
                                   billing_flow="assigned")
    inv_b1_paid = _make_invoice(comp_b.id, brand_b1.id, user_b1.id,
                                 status="paid", total_amount=Decimal("300.00"),
                                 billing_flow="assigned")
    admin_db_session.add_all([inv_a1_paid, inv_a1_sent, inv_a2_finalized, inv_a1_voided, inv_b1_paid])
    await admin_db_session.flush()

    # Approval requests
    now = datetime.now(UTC)
    appr_pending = _make_approval(comp_a.id, brand_a1.id, user_a1.id, status="pending")
    appr_approved = _make_approval(comp_a.id, brand_a1.id, user_a1.id,
                                    status="approved",
                                    decided_by=user_a1.id,
                                    decided_at=now,
                                    requested_at=now - timedelta(hours=2))
    appr_rejected = _make_approval(comp_a.id, brand_a1.id, user_a1.id,
                                    status="rejected",
                                    decided_by=user_a1.id,
                                    decided_at=now,
                                    requested_at=now - timedelta(hours=4))
    appr_b1 = _make_approval(comp_b.id, brand_b1.id, user_b1.id, status="approved",
                              decided_by=user_b1.id,
                              decided_at=now,
                              requested_at=now - timedelta(hours=1))
    admin_db_session.add_all([appr_pending, appr_approved, appr_rejected, appr_b1])
    await admin_db_session.flush()

    return {
        "comp_a": comp_a, "brand_a1": brand_a1, "brand_a2": brand_a2,
        "comp_b": comp_b, "brand_b1": brand_b1,
        "user_a1": user_a1, "user_a2": user_a2, "user_b1": user_b1,
        "cat_a1": cat_a1, "cat_a2": cat_a2, "cat_b1": cat_b1,
        "prod_a1": prod_a1, "prod_a2": prod_a2, "prod_b1": prod_b1,
        "order_a1_1": order_a1_1, "order_a1_2": order_a1_2,
        "order_a2_1": order_a2_1, "order_b1_1": order_b1_1,
        "bulk_a1": bulk_a1, "bulk_b1": bulk_b1,
        "inv_a1_paid": inv_a1_paid, "inv_a1_sent": inv_a1_sent,
        "inv_a2_finalized": inv_a2_finalized, "inv_b1_paid": inv_b1_paid,
    }


# ===========================================================================
# FUNCTIONAL TESTS — use admin_db_session (superuser, sees everything)
# ===========================================================================
class TestSpendSummary:
    async def test_spend_summary_calculates_totals(self, admin_db_session, analytics_data):
        """Verify correct aggregation of individual + bulk order amounts."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_spend_summary()

        # Company A individual: 150 + 75 + 200 = 425
        # Company B individual: 300
        # Company A bulk: 500
        # Company B bulk: 400
        # Total individual: 725, Total bulk: 900, Total: 1625
        # Order count: 4 individual (approved/delivered) + 2 bulk = 6
        assert result["individual_order_spend"] == Decimal("725.00")
        assert result["bulk_order_spend"] == Decimal("900.00")
        assert result["total_spend"] == Decimal("1625.00")
        assert result["order_count"] == 6
        assert result["average_order_value"] == result["total_spend"] / 6

    async def test_spend_summary_excludes_cancelled_orders(self, admin_db_session, analytics_data):
        """Cancelled and pending orders are excluded from spend."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_spend_summary()

        # 999 (cancelled) and 50 (pending) should NOT be in total
        assert Decimal("999.00") not in [result["total_spend"]]
        assert result["total_spend"] == Decimal("1625.00")

    async def test_spend_summary_with_date_range(self, admin_db_session, analytics_data):
        """Date filtering excludes orders outside the range."""
        service = AnalyticsService(admin_db_session)

        # Set a date range that's in the future — should return zero
        future = date.today() + timedelta(days=30)
        result = await service.get_spend_summary(start_date=future)
        assert result["total_spend"] == Decimal(0)
        assert result["order_count"] == 0

    async def test_spend_summary_empty_database(self, admin_db_session, company_a):
        """Returns zeros when no orders exist."""
        service = AnalyticsService(admin_db_session)
        # Use a date range that excludes everything
        future = date.today() + timedelta(days=365)
        result = await service.get_spend_summary(start_date=future)
        assert result["total_spend"] == Decimal(0)
        assert result["order_count"] == 0
        assert result["average_order_value"] == Decimal(0)


class TestSpendBySubBrand:
    async def test_spend_by_sub_brand_groups_correctly(self, admin_db_session, analytics_data):
        """Breakdowns match per-brand totals, including both individual and bulk."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_spend_by_sub_brand()

        brands = {r["sub_brand_name"]: r for r in result}

        # Brand A1: individual 150+75=225, bulk 500 = 725
        assert brands["Brand A1"]["total_spend"] == Decimal("725.00")
        assert brands["Brand A1"]["order_count"] == 3  # 2 individual + 1 bulk

        # Brand A2: individual 200, no bulk = 200
        assert brands["Brand A2"]["total_spend"] == Decimal("200.00")
        assert brands["Brand A2"]["order_count"] == 1

        # Brand B1: individual 300, bulk 400 = 700
        assert brands["Brand B1"]["total_spend"] == Decimal("700.00")
        assert brands["Brand B1"]["order_count"] == 2


class TestSpendOverTime:
    async def test_spend_over_time_monthly_buckets(self, admin_db_session, analytics_data):
        """Time series returns correct period labels and totals."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_spend_over_time(granularity="month")

        # All orders were created "today", so they should all be in one month bucket
        assert len(result) >= 1
        total = sum(r["total_spend"] for r in result)
        assert total == Decimal("1625.00")


class TestOrderStatusBreakdown:
    async def test_order_status_breakdown(self, admin_db_session, analytics_data):
        """Count of orders by status, separated by order type."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_order_status_breakdown()

        ind_statuses = {r["status"]: r["count"] for r in result if r["order_type"] == "individual"}
        bulk_statuses = {r["status"]: r["count"] for r in result if r["order_type"] == "bulk"}

        # Individual: 3 approved (incl Company B), 1 delivered, 1 cancelled, 1 pending
        assert ind_statuses.get("approved", 0) == 3
        assert ind_statuses.get("delivered", 0) == 1
        assert ind_statuses.get("cancelled", 0) == 1
        assert ind_statuses.get("pending", 0) == 1

        # Bulk: 2 approved
        assert bulk_statuses.get("approved", 0) == 2


class TestTopProducts:
    async def test_top_products_ranked_by_quantity(self, admin_db_session, analytics_data):
        """Most ordered products appear first."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_top_products(limit=5)

        # prod_a1 (Widget Alpha): ind 3+1+4=8, bulk 10 = 18 total
        # prod_a2 (Widget Beta): ind 3 = 3 total
        # prod_b1 (Gadget One): ind 6, bulk 8 = 14 total
        assert len(result) >= 3
        assert result[0]["product_name"] == "Widget Alpha"
        assert result[0]["total_quantity"] == 18
        assert result[1]["product_name"] == "Gadget One"
        assert result[1]["total_quantity"] == 14
        assert result[2]["product_name"] == "Widget Beta"
        assert result[2]["total_quantity"] == 3


class TestSizeDistribution:
    async def test_size_distribution_includes_bulk_and_individual(self, admin_db_session, analytics_data):
        """Both order types counted in size distribution."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_size_distribution()

        sizes = {r["size"]: r["count"] for r in result}

        # M: ind 3 (li_a1_1) + ind 6 (li_b1_1) = 9
        assert sizes.get("M") == 9
        # L: ind 3 (li_a1_2) + bulk 10 (bi_a1) = 13
        assert sizes.get("L") == 13
        # S: ind 1 (li_a1_3) = 1
        assert sizes.get("S") == 1
        # XL: ind 4 (li_a2_1) + bulk 8 (bi_b1) = 12
        assert sizes.get("XL") == 12

        # Percentages should sum to ~100
        total_pct = sum(r["percentage"] for r in result)
        assert abs(total_pct - 100.0) < 0.1


class TestInvoiceSummary:
    async def test_invoice_summary_totals(self, admin_db_session, analytics_data):
        """Invoice amounts by status sum correctly."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_invoice_summary()

        # Paid: 150 (A) + 300 (B) = 450
        assert result["total_paid"] == Decimal("450.00")
        # Total invoiced (all non-voided): 150 + 75 + 200 + 300 = 725
        assert result["total_invoiced"] == Decimal("725.00")
        # Invoice count: 5 total
        assert result["invoice_count"] == 5

    async def test_invoice_summary_outstanding_calculation(self, admin_db_session, analytics_data):
        """Outstanding = finalized + sent (not paid/voided)."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_invoice_summary()

        # Outstanding: sent 75 + finalized 200 = 275
        assert result["total_outstanding"] == Decimal("275.00")

    async def test_invoice_summary_by_billing_flow(self, admin_db_session, analytics_data):
        """By billing flow groups are correct."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_invoice_summary()

        flows = {r["billing_flow"]: r for r in result["by_billing_flow"]}
        # assigned: paid 150, sent 0, voided 999, paid_b 300 = 3 invoices
        assert flows["assigned"]["count"] == 3
        assert flows["self_service"]["count"] == 1
        assert flows["post_window"]["count"] == 1


class TestApprovalMetrics:
    async def test_approval_metrics_approval_rate(self, admin_db_session, analytics_data):
        """Rate calculation is correct: approved / (approved + rejected)."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_approval_metrics()

        # Pending: 1, Approved: 2 (A1 + B1), Rejected: 1
        assert result["pending_count"] == 1
        assert result["approved_count"] == 2
        assert result["rejected_count"] == 1
        # Rate: 2 / (2 + 1) = 0.6667
        assert abs(result["approval_rate"] - 0.6667) < 0.001

    async def test_approval_metrics_avg_time(self, admin_db_session, analytics_data):
        """Average time calculation handles decided requests."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_approval_metrics()

        # Decided: 2h, 4h, 1h — average = (2+4+1)/3 = 2.333h
        assert result["avg_approval_time_hours"] is not None
        assert abs(result["avg_approval_time_hours"] - 2.33) < 0.1

    async def test_approval_metrics_no_decisions(self, admin_db_session, company_a):
        """avg_approval_time_hours is None when no decisions exist."""
        service = AnalyticsService(admin_db_session)
        # Use a date range that excludes existing data
        future = date.today() + timedelta(days=365)
        result = await service.get_approval_metrics(start_date=future)
        assert result["avg_approval_time_hours"] is None
        assert result["approval_rate"] == 0.0


class TestPlatformOverview:
    async def test_platform_overview_counts(self, admin_db_session, analytics_data):
        """All entity counts are correct (sees all companies)."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_platform_overview()

        # At minimum: 2 companies (A, B) — could be more from other fixtures
        assert result["total_companies"] >= 2
        # At minimum: 3 sub-brands (A1, A2, B1)
        assert result["total_sub_brands"] >= 3
        # At minimum: 3 analytics users
        assert result["total_users"] >= 3
        # 6 orders total (incl cancelled/pending)
        assert result["total_orders"] >= 6
        # Revenue = paid invoices: 150 + 300 = 450
        assert result["total_revenue"] >= Decimal("450.00")
        # Active catalogs: 3
        assert result["active_catalogs"] >= 3


class TestRevenueByCompany:
    async def test_revenue_by_company_correct(self, admin_db_session, analytics_data):
        """Revenue attributed to correct companies."""
        service = AnalyticsService(admin_db_session)
        result = await service.get_revenue_by_company()

        companies = {r["company_name"]: r for r in result}
        # Company A: paid 150
        assert companies["Company A"]["total_revenue"] == Decimal("150.00")
        assert companies["Company A"]["invoice_count"] == 1
        # Company B: paid 300
        assert companies["Company B"]["total_revenue"] == Decimal("300.00")
        assert companies["Company B"]["invoice_count"] == 1


# ===========================================================================
# ISOLATION TESTS — use db_session (reel48_app, RLS enforced)
#
# These tests seed data via admin_factory (committed), query via app_factory
# (RLS enforced), and clean up in a finally block.
# ===========================================================================

async def _set_tenant_context(session, company_id, sub_brand_id):
    """
    Helper to set PostgreSQL session variables for RLS.

    IMPORTANT: Both company_id and sub_brand_id MUST be real UUIDs when testing
    with the non-superuser reel48_app role. PostgreSQL does not guarantee
    short-circuit evaluation of OR in RLS policies, so setting a variable to ''
    can cause the `::uuid` cast in the third OR branch to fail even though the
    second branch (= '') is true. The actual application always goes through
    the client fixture (superuser session), which bypasses RLS. Isolation tests
    are the only code path that hits RLS evaluation directly.
    """
    await session.execute(text(f"SET LOCAL app.current_company_id = '{company_id}'"))
    await session.execute(text(f"SET LOCAL app.current_sub_brand_id = '{sub_brand_id}'"))


async def _seed_isolation_data(admin_factory):
    """Create and COMMIT multi-tenant data for isolation tests. Returns entity IDs for cleanup."""
    async with admin_factory() as seed:
        # Companies
        comp_a = Company(name="Iso Company A", slug=f"iso-a-{uuid4().hex[:6]}", is_active=True)
        comp_b = Company(name="Iso Company B", slug=f"iso-b-{uuid4().hex[:6]}", is_active=True)
        seed.add_all([comp_a, comp_b])
        await seed.flush()

        brand_a1 = SubBrand(company_id=comp_a.id, name="Iso Brand A1", slug="iso-a1", is_default=True)
        brand_b1 = SubBrand(company_id=comp_b.id, name="Iso Brand B1", slug="iso-b1", is_default=True)
        seed.add_all([brand_a1, brand_b1])
        await seed.flush()

        user_a = User(company_id=comp_a.id, sub_brand_id=brand_a1.id, cognito_sub=str(uuid4()),
                      email=f"iso-a-{uuid4().hex[:6]}@a.com", full_name="Iso A", role="employee")
        user_b = User(company_id=comp_b.id, sub_brand_id=brand_b1.id, cognito_sub=str(uuid4()),
                      email=f"iso-b-{uuid4().hex[:6]}@b.com", full_name="Iso B", role="employee")
        seed.add_all([user_a, user_b])
        await seed.flush()

        cat_a = _make_catalog(comp_a.id, brand_a1.id, user_a.id)
        cat_b = _make_catalog(comp_b.id, brand_b1.id, user_b.id)
        seed.add_all([cat_a, cat_b])
        await seed.flush()

        prod_a = _make_product(comp_a.id, brand_a1.id, user_a.id)
        prod_b = _make_product(comp_b.id, brand_b1.id, user_b.id)
        seed.add_all([prod_a, prod_b])
        await seed.flush()

        # Orders
        order_a = _make_order(comp_a.id, brand_a1.id, user_a.id, cat_a.id,
                              total_amount=Decimal("100.00"))
        order_b = _make_order(comp_b.id, brand_b1.id, user_b.id, cat_b.id,
                              total_amount=Decimal("200.00"))
        seed.add_all([order_a, order_b])
        await seed.flush()

        # Bulk orders
        bulk_a = _make_bulk_order(comp_a.id, brand_a1.id, cat_a.id, user_a.id,
                                  total_amount=Decimal("300.00"))
        bulk_b = _make_bulk_order(comp_b.id, brand_b1.id, cat_b.id, user_b.id,
                                  total_amount=Decimal("400.00"))
        seed.add_all([bulk_a, bulk_b])
        await seed.flush()

        # Invoices
        inv_a = _make_invoice(comp_a.id, brand_a1.id, user_a.id,
                               status="paid", total_amount=Decimal("100.00"))
        inv_b = _make_invoice(comp_b.id, brand_b1.id, user_b.id,
                               status="paid", total_amount=Decimal("200.00"))
        seed.add_all([inv_a, inv_b])
        await seed.flush()

        data = {
            "comp_a_id": comp_a.id, "comp_b_id": comp_b.id,
            "brand_a1_id": brand_a1.id, "brand_b1_id": brand_b1.id,
            "user_a_id": user_a.id, "user_b_id": user_b.id,
            "cat_a_id": cat_a.id, "cat_b_id": cat_b.id,
            "prod_a_id": prod_a.id, "prod_b_id": prod_b.id,
            "order_a_id": order_a.id, "order_b_id": order_b.id,
            "bulk_a_id": bulk_a.id, "bulk_b_id": bulk_b.id,
            "inv_a_id": inv_a.id, "inv_b_id": inv_b.id,
        }
        await seed.commit()
        return data


async def _cleanup_isolation_data(admin_factory, data):
    """Delete seeded isolation test data in reverse FK order."""
    async with admin_factory() as cleanup:
        for table in ["invoices", "bulk_orders", "orders", "products", "catalogs",
                       "users", "sub_brands", "companies"]:
            if table == "companies":
                ids = [data["comp_a_id"], data["comp_b_id"]]
            elif table == "sub_brands":
                ids = [data["brand_a1_id"], data["brand_b1_id"]]
            elif table == "users":
                ids = [data["user_a_id"], data["user_b_id"]]
            elif table == "catalogs":
                ids = [data["cat_a_id"], data["cat_b_id"]]
            elif table == "products":
                ids = [data["prod_a_id"], data["prod_b_id"]]
            elif table == "orders":
                ids = [data["order_a_id"], data["order_b_id"]]
            elif table == "bulk_orders":
                ids = [data["bulk_a_id"], data["bulk_b_id"]]
            elif table == "invoices":
                ids = [data["inv_a_id"], data["inv_b_id"]]
            else:
                continue
            for row_id in ids:
                await cleanup.execute(
                    text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id}  # noqa: S608
                )
        await cleanup.commit()


class TestSpendSummaryIsolation:
    async def test_spend_summary_company_isolation(self, setup_database):
        """Company A's analytics do NOT include Company B's orders."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]
        data = await _seed_isolation_data(admin_factory)

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, data["comp_a_id"], data["brand_a1_id"])
                    service = AnalyticsService(app_sess)
                    result = await service.get_spend_summary()

                    # Company A, Brand A1 only: individual 100, bulk 300
                    # Company B's orders should NOT be included
                    assert result["individual_order_spend"] == Decimal("100.00")
                    assert result["bulk_order_spend"] == Decimal("300.00")
                    assert result["total_spend"] == Decimal("400.00")
        finally:
            await _cleanup_isolation_data(admin_factory, data)

    async def test_spend_by_sub_brand_isolation(self, setup_database):
        """Sub-brand scoped user sees only their brand's data."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]
        data = await _seed_isolation_data(admin_factory)

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, data["comp_a_id"], data["brand_a1_id"])
                    service = AnalyticsService(app_sess)
                    result = await service.get_spend_by_sub_brand()

                    brand_names = [r["sub_brand_name"] for r in result]
                    assert "Iso Brand A1" in brand_names
                    assert "Iso Brand B1" not in brand_names
        finally:
            await _cleanup_isolation_data(admin_factory, data)


class TestInvoiceSummaryIsolation:
    async def test_invoice_summary_company_isolation(self, setup_database):
        """Company B's invoices not visible to Company A."""
        admin_factory = setup_database["admin_factory"]
        app_factory = setup_database["app_factory"]
        data = await _seed_isolation_data(admin_factory)

        try:
            async with app_factory() as app_sess:
                async with app_sess.begin():
                    await _set_tenant_context(app_sess, data["comp_a_id"], data["brand_a1_id"])
                    service = AnalyticsService(app_sess)
                    result = await service.get_invoice_summary()

                    # Company A, Brand A1 only: 1 paid invoice for 100
                    assert result["total_paid"] == Decimal("100.00")
                    assert result["invoice_count"] == 1
        finally:
            await _cleanup_isolation_data(admin_factory, data)


class TestPlatformOverviewIsolation:
    async def test_platform_overview_sees_all_companies(self, admin_db_session, analytics_data):
        """
        reel48_admin sees all data. Tested via admin_db_session (superuser) because
        the companies table RLS policy casts company_id to UUID, which fails with
        empty-string bypass on the non-superuser role. In production, reel48_admin
        queries go through the client fixture which uses the same superuser session.
        """
        service = AnalyticsService(admin_db_session)
        result = await service.get_platform_overview()

        # Should see all companies from analytics_data
        assert result["total_companies"] >= 2
        assert result["total_orders"] >= 6


# ===========================================================================
# API ENDPOINT TESTS — Module 8 Phase 2
#
# These tests verify the HTTP layer: routing, authorization guards,
# query parameters, response shapes, and tenant isolation via the API.
# ===========================================================================

# All analytics endpoints (for parametrized auth tests)
_ANALYTICS_ENDPOINTS = [
    "/api/v1/analytics/spend/summary",
    "/api/v1/analytics/spend/by-sub-brand",
    "/api/v1/analytics/spend/over-time",
    "/api/v1/analytics/orders/status-breakdown",
    "/api/v1/analytics/orders/top-products",
    "/api/v1/analytics/orders/size-distribution",
    "/api/v1/analytics/invoices/summary",
    "/api/v1/analytics/approvals/metrics",
]

# Endpoints accessible to regional_manager (excludes by-sub-brand, invoice summary)
_MANAGER_ENDPOINTS = [
    "/api/v1/analytics/spend/summary",
    "/api/v1/analytics/spend/over-time",
    "/api/v1/analytics/orders/status-breakdown",
    "/api/v1/analytics/orders/top-products",
    "/api/v1/analytics/orders/size-distribution",
    "/api/v1/analytics/approvals/metrics",
]

# Endpoints requiring corporate_admin
_CORPORATE_ONLY_ENDPOINTS = [
    "/api/v1/analytics/spend/by-sub-brand",
    "/api/v1/analytics/invoices/summary",
]


class TestAnalyticsAPIFunctional:
    """Functional tests for analytics API endpoints."""

    async def test_spend_summary_endpoint_returns_200(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Corporate admin gets a valid spend summary response."""
        response = await client.get(
            "/api/v1/analytics/spend/summary",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        data = body["data"]
        assert "total_spend" in data
        assert "order_count" in data
        assert "average_order_value" in data
        assert "individual_order_spend" in data
        assert "bulk_order_spend" in data

    async def test_spend_over_time_with_granularity_param(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Granularity query param is accepted and works."""
        response = await client.get(
            "/api/v1/analytics/spend/over-time?granularity=week",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["data"], list)

    async def test_top_products_with_limit_param(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Limit query param constrains result count."""
        response = await client.get(
            "/api/v1/analytics/orders/top-products?limit=5",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["data"], list)
        assert len(body["data"]) <= 5

    async def test_date_range_filtering_via_query_params(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Date range params filter results. Future dates yield zero."""
        response = await client.get(
            "/api/v1/analytics/spend/summary?start_date=2099-01-01&end_date=2099-12-31",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_spend"] == 0
        assert data["order_count"] == 0

    async def test_invoice_summary_endpoint(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Invoice summary returns correct structure."""
        response = await client.get(
            "/api/v1/analytics/invoices/summary",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "total_invoiced" in data
        assert "total_paid" in data
        assert "total_outstanding" in data
        assert "invoice_count" in data
        assert "by_status" in data
        assert "by_billing_flow" in data

    async def test_order_status_breakdown_endpoint(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Order status breakdown returns list with correct structure."""
        response = await client.get(
            "/api/v1/analytics/orders/status-breakdown",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        if data:
            assert "status" in data[0]
            assert "count" in data[0]
            assert "order_type" in data[0]

    async def test_size_distribution_endpoint(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Size distribution returns list with correct structure."""
        response = await client.get(
            "/api/v1/analytics/orders/size-distribution",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        if data:
            assert "size" in data[0]
            assert "count" in data[0]
            assert "percentage" in data[0]

    async def test_approval_metrics_endpoint(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Approval metrics returns correct structure."""
        response = await client.get(
            "/api/v1/analytics/approvals/metrics",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "pending_count" in data
        assert "approved_count" in data
        assert "rejected_count" in data
        assert "approval_rate" in data
        assert "avg_approval_time_hours" in data

    async def test_spend_by_sub_brand_endpoint(
        self, client, analytics_data, company_a_corporate_admin_token
    ):
        """Spend by sub-brand returns list with correct structure."""
        response = await client.get(
            "/api/v1/analytics/spend/by-sub-brand",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        if data:
            assert "sub_brand_id" in data[0]
            assert "sub_brand_name" in data[0]
            assert "total_spend" in data[0]
            assert "order_count" in data[0]


class TestAnalyticsAPIAuthorization:
    """Authorization tests — verify role restrictions on all endpoints."""

    @pytest.mark.parametrize("endpoint", _ANALYTICS_ENDPOINTS)
    async def test_employee_gets_403_on_all_analytics(
        self, client, company_a, company_a_brand_a1_employee_token, endpoint
    ):
        """Employee token gets 403 on every analytics endpoint."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint", _ANALYTICS_ENDPOINTS)
    async def test_unauthenticated_gets_401(self, client, endpoint):
        """No token returns 401 on every analytics endpoint."""
        response = await client.get(endpoint)
        assert response.status_code in (401, 403)  # HTTPBearer returns 403 for missing token

    async def test_sub_brand_admin_cannot_see_spend_by_sub_brand(
        self, client, company_a, company_a_brand_a1_admin_token
    ):
        """sub_brand_admin gets 403 on spend/by-sub-brand (corporate_admin only)."""
        response = await client.get(
            "/api/v1/analytics/spend/by-sub-brand",
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_cannot_see_invoice_summary(
        self, client, company_a, company_a_brand_a1_admin_token
    ):
        """sub_brand_admin gets 403 on invoices/summary (corporate_admin only)."""
        response = await client.get(
            "/api/v1/analytics/invoices/summary",
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_regional_manager_cannot_see_spend_by_sub_brand(
        self, client, company_a, company_a_brand_a1_manager_token
    ):
        """regional_manager gets 403 on spend/by-sub-brand."""
        response = await client.get(
            "/api/v1/analytics/spend/by-sub-brand",
            headers={"Authorization": f"Bearer {company_a_brand_a1_manager_token}"},
        )
        assert response.status_code == 403

    async def test_regional_manager_cannot_see_invoice_summary(
        self, client, company_a, company_a_brand_a1_manager_token
    ):
        """regional_manager gets 403 on invoices/summary."""
        response = await client.get(
            "/api/v1/analytics/invoices/summary",
            headers={"Authorization": f"Bearer {company_a_brand_a1_manager_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint", _MANAGER_ENDPOINTS)
    async def test_regional_manager_can_see_manager_endpoints(
        self, client, company_a, company_a_brand_a1_manager_token, endpoint
    ):
        """regional_manager gets 200 on non-corporate-only endpoints."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_brand_a1_manager_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("endpoint", _ANALYTICS_ENDPOINTS)
    async def test_corporate_admin_can_see_all_endpoints(
        self, client, analytics_data, company_a_corporate_admin_token, endpoint
    ):
        """corporate_admin gets 200 on every analytics endpoint."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("endpoint", _MANAGER_ENDPOINTS)
    async def test_sub_brand_admin_can_see_manager_endpoints(
        self, client, company_a, company_a_brand_a1_admin_token, endpoint
    ):
        """sub_brand_admin gets 200 on non-corporate-only endpoints."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 200


# ===========================================================================
# PLATFORM ANALYTICS API TESTS — Module 8 Phase 3
#
# These tests verify the platform admin analytics endpoints under
# /api/v1/platform/analytics/. Only reel48_admin can access them.
# ===========================================================================

_PLATFORM_ANALYTICS_ENDPOINTS = [
    "/api/v1/platform/analytics/overview",
    "/api/v1/platform/analytics/revenue/by-company",
    "/api/v1/platform/analytics/revenue/over-time",
    "/api/v1/platform/analytics/orders/status-breakdown",
    "/api/v1/platform/analytics/orders/top-products",
    "/api/v1/platform/analytics/invoices/summary",
    "/api/v1/platform/analytics/approvals/metrics",
]


class TestPlatformAnalyticsAPIFunctional:
    """Functional tests for platform analytics endpoints."""

    async def test_platform_overview_returns_correct_counts(
        self, client, analytics_data, reel48_admin_token
    ):
        """All entity counts match seeded data."""
        response = await client.get(
            "/api/v1/platform/analytics/overview",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_companies"] >= 2
        assert data["total_sub_brands"] >= 3
        assert data["total_users"] >= 3
        assert data["total_orders"] >= 6
        assert data["total_revenue"] >= 450  # paid invoices: 150 + 300
        assert data["active_catalogs"] >= 3

    async def test_platform_revenue_by_company_lists_all_companies(
        self, client, analytics_data, reel48_admin_token
    ):
        """Both Company A and B appear in revenue breakdown."""
        response = await client.get(
            "/api/v1/platform/analytics/revenue/by-company",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        company_names = {r["company_name"] for r in data}
        assert "Company A" in company_names
        assert "Company B" in company_names

    async def test_platform_revenue_over_time(
        self, client, analytics_data, reel48_admin_token
    ):
        """Time series includes all companies' order data."""
        response = await client.get(
            "/api/v1/platform/analytics/revenue/over-time?granularity=month",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        # Total should include both companies' order spend
        total = sum(r["total_spend"] for r in data)
        assert total >= 1625  # 725 (ind) + 900 (bulk) from analytics_data

    async def test_platform_order_breakdown_cross_company(
        self, client, analytics_data, reel48_admin_token
    ):
        """Status counts span all companies."""
        response = await client.get(
            "/api/v1/platform/analytics/orders/status-breakdown",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        # Should have entries for both individual and bulk orders
        order_types = {r["order_type"] for r in data}
        assert "individual" in order_types
        assert "bulk" in order_types
        # Total individual count: 6 (3 approved + 1 delivered + 1 cancelled + 1 pending)
        ind_total = sum(r["count"] for r in data if r["order_type"] == "individual")
        assert ind_total >= 6

    async def test_platform_top_products_cross_company(
        self, client, analytics_data, reel48_admin_token
    ):
        """Products from all companies ranked together."""
        response = await client.get(
            "/api/v1/platform/analytics/orders/top-products?limit=10",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 3
        # Widget Alpha (18), Gadget One (14), Widget Beta (3)
        product_names = [r["product_name"] for r in data]
        assert "Widget Alpha" in product_names
        assert "Gadget One" in product_names
        assert "Widget Beta" in product_names

    async def test_platform_invoice_summary_cross_company(
        self, client, analytics_data, reel48_admin_token
    ):
        """All invoices across all companies included."""
        response = await client.get(
            "/api/v1/platform/analytics/invoices/summary",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        # 5 total invoices: paid A 150, sent A 75, finalized A 200, voided A 999, paid B 300
        assert data["invoice_count"] >= 5
        assert data["total_paid"] >= 450  # 150 + 300
        assert "by_status" in data
        assert "by_billing_flow" in data

    async def test_platform_approval_metrics_cross_company(
        self, client, analytics_data, reel48_admin_token
    ):
        """Approval metrics span all companies."""
        response = await client.get(
            "/api/v1/platform/analytics/approvals/metrics",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pending_count"] >= 1
        assert data["approved_count"] >= 2  # A1 + B1
        assert data["rejected_count"] >= 1
        assert "approval_rate" in data
        assert "avg_approval_time_hours" in data


class TestPlatformAnalyticsAPIAuthorization:
    """Authorization tests — only reel48_admin can access platform analytics."""

    @pytest.mark.parametrize("endpoint", _PLATFORM_ANALYTICS_ENDPOINTS)
    async def test_corporate_admin_gets_403_on_platform_analytics(
        self, client, company_a, company_a_corporate_admin_token, endpoint
    ):
        """corporate_admin gets 403 on platform analytics endpoints."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint", _PLATFORM_ANALYTICS_ENDPOINTS)
    async def test_sub_brand_admin_gets_403_on_platform_analytics(
        self, client, company_a, company_a_brand_a1_admin_token, endpoint
    ):
        """sub_brand_admin gets 403 on platform analytics endpoints."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint", _PLATFORM_ANALYTICS_ENDPOINTS)
    async def test_employee_gets_403_on_platform_analytics(
        self, client, company_a, company_a_brand_a1_employee_token, endpoint
    ):
        """employee gets 403 on platform analytics endpoints."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint", _PLATFORM_ANALYTICS_ENDPOINTS)
    async def test_reel48_admin_gets_200_on_all_platform_endpoints(
        self, client, analytics_data, reel48_admin_token, endpoint
    ):
        """reel48_admin gets 200 on every platform analytics endpoint."""
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200


class TestAnalyticsAPIIsolation:
    """Isolation tests — verify tenant boundaries via API.

    NOTE: The `client` fixture uses admin_db_session (superuser), which
    bypasses RLS. True data isolation is already verified at the service
    level in TestSpendSummaryIsolation and TestInvoiceSummaryIsolation above
    (using reel48_app role with RLS enforced). These API-level tests verify
    that different-company tokens are accepted and return valid responses,
    confirming the auth layer allows cross-company access without errors.
    """

    async def test_company_b_admin_sees_valid_spend_summary(
        self, client, analytics_data, company_b_corporate_admin_token
    ):
        """Company B corporate admin can access spend summary endpoint."""
        response = await client.get(
            "/api/v1/analytics/spend/summary",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "total_spend" in data
        assert "order_count" in data
        # Data isolation is verified at the service level (TestSpendSummaryIsolation)

    async def test_sub_brand_a1_admin_can_access_spend_summary(
        self, client, analytics_data, company_a_brand_a1_admin_token
    ):
        """Brand A1 admin can access spend summary (scoped by RLS in prod)."""
        response = await client.get(
            "/api/v1/analytics/spend/summary",
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "individual_order_spend" in data
        assert "bulk_order_spend" in data
        # Sub-brand isolation is verified at the service level (TestSpendSummaryIsolation)

    async def test_company_b_admin_can_access_invoice_summary(
        self, client, analytics_data, company_b_corporate_admin_token
    ):
        """Company B corporate admin can access invoice summary."""
        response = await client.get(
            "/api/v1/analytics/invoices/summary",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "total_paid" in data
        assert "invoice_count" in data
        # Company isolation is verified at the service level (TestInvoiceSummaryIsolation)
