"""Tests for Module 6 Phase 3: Approval queue endpoints, decision endpoints,
approval rules endpoints, and integration with submit/create flows."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest
from app.models.approval_rule import ApprovalRule
from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.product import Product
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_product(
    db: AsyncSession, company_id, sub_brand_id, created_by,
    *, status: str = "draft",
) -> Product:
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Product {uuid4().hex[:6]}",
        sku=f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=Decimal("29.99"),
        sizes=["S", "M", "L"],
        decoration_options=[],
        image_urls=[],
        status=status,
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _create_catalog(
    db: AsyncSession, company_id, sub_brand_id, created_by,
    *, status: str = "active", payment_model: str = "self_service",
) -> Catalog:
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Catalog {uuid4().hex[:6]}",
        slug=f"catalog-{uuid4().hex[:6]}",
        payment_model=payment_model,
        status=status,
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _create_catalog_with_product(
    db: AsyncSession, company_id, sub_brand_id, created_by,
) -> tuple[Catalog, Product]:
    """Create an active catalog with one active product (for order creation)."""
    product = await _create_product(
        db, company_id, sub_brand_id, created_by, status="active",
    )
    catalog = await _create_catalog(
        db, company_id, sub_brand_id, created_by, status="active",
    )
    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()
    return catalog, product


async def _create_submitted_catalog_with_product(
    db: AsyncSession, company_id, sub_brand_id, created_by,
) -> Catalog:
    """Create a submitted catalog with one active product."""
    product = await _create_product(
        db, company_id, sub_brand_id, created_by, status="active",
    )
    catalog = await _create_catalog(
        db, company_id, sub_brand_id, created_by, status="submitted",
    )
    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()
    return catalog


async def _create_pending_order(
    db: AsyncSession, company_id, sub_brand_id, user_id, catalog_id,
    *, total_amount=Decimal("100.00"),
) -> Order:
    order = Order(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user_id,
        catalog_id=catalog_id,
        order_number=f"ORD-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}",
        status="pending",
        subtotal=total_amount,
        total_amount=total_amount,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order


async def _create_submitted_bulk_order(
    db: AsyncSession, company_id, sub_brand_id, created_by, catalog_id,
    *, total_amount=Decimal("500.00"),
) -> BulkOrder:
    bulk_order = BulkOrder(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        catalog_id=catalog_id,
        created_by=created_by,
        title=f"Bulk Order {uuid4().hex[:6]}",
        order_number=f"BLK-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}",
        status="submitted",
        total_items=10,
        total_amount=total_amount,
        submitted_at=datetime.now(UTC),
    )
    db.add(bulk_order)
    await db.flush()
    await db.refresh(bulk_order)
    return bulk_order


async def _create_approval_request(
    db: AsyncSession, entity_type, entity_id, company_id, sub_brand_id,
    requested_by, *, status="pending",
) -> ApprovalRequest:
    ar = ApprovalRequest(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        entity_type=entity_type,
        entity_id=entity_id,
        requested_by=requested_by,
        status=status,
        requested_at=datetime.now(UTC),
    )
    if status != "pending":
        ar.decided_by = requested_by  # type: ignore[assignment]
        ar.decided_at = datetime.now(UTC)  # type: ignore[assignment]
    db.add(ar)
    await db.flush()
    await db.refresh(ar)
    return ar


# ===========================================================================
# Approval Queue Endpoint Tests
# ===========================================================================


class TestPendingQueue:
    async def test_list_pending_as_manager(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a1_employee,
    ):
        """Manager sees pending orders in their sub-brand."""
        company, brand_a1, _a2 = company_a
        catalog, product = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
        )
        await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/approvals/pending/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1
        assert any(item["entity_id"] == str(order.id) for item in data)

    async def test_list_pending_with_entity_type_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_admin_token, user_a1_employee,
    ):
        """Filter pending queue by entity_type."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.get(
            "/api/v1/approvals/pending/?entity_type=product",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["entity_type"] == "product" for item in data)

    async def test_employee_gets_403_on_pending(
        self, client: AsyncClient,
        company_a, user_a1_employee_token,
    ):
        """Employees cannot access the approval queue."""
        response = await client.get(
            "/api/v1/approvals/pending/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_regional_manager_only_sees_orders_and_bulk_orders(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a1_admin, user_a1_employee,
    ):
        """Regional manager sees only orders/bulk_orders, not products/catalogs."""
        company, brand_a1, _a2 = company_a
        # Create a product approval request
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )
        # Create an order approval request
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
        )
        await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/approvals/pending/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        entity_types = {item["entity_type"] for item in data}
        assert "product" not in entity_types
        assert "catalog" not in entity_types


class TestApprovalHistory:
    async def test_list_history_returns_decided_items(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_admin_token, reel48_admin_user,
    ):
        """History endpoint returns approved/rejected items."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
            status="approved",
        )

        response = await client.get(
            "/api/v1/approvals/history/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1

    async def test_history_status_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_admin_token,
    ):
        """Filter history by status."""
        company, brand_a1, _a2 = company_a
        p1 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        p2 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", p1.id,
            company.id, brand_a1.id, user_a1_admin.id,
            status="approved",
        )
        await _create_approval_request(
            admin_db_session, "product", p2.id,
            company.id, brand_a1.id, user_a1_admin.id,
            status="rejected",
        )

        response = await client.get(
            "/api/v1/approvals/history/?status=approved",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["status"] == "approved" for item in data)

    async def test_employee_gets_403_on_history(
        self, client: AsyncClient, company_a, user_a1_employee_token,
    ):
        response = await client.get(
            "/api/v1/approvals/history/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


class TestGetApprovalRequest:
    async def test_get_approval_request_detail(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_admin_token,
    ):
        """Get a single approval request by ID."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.get(
            f"/api/v1/approvals/{ar.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(ar.id)
        assert data["entity_type"] == "product"
        assert data["status"] == "pending"


# ===========================================================================
# Approval Decision Endpoint Tests
# ===========================================================================


class TestApproveDecision:
    async def test_approve_product_via_unified_endpoint(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user,
        reel48_admin_user_token,
    ):
        """Approve a product through the unified approval endpoint."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.post(
            f"/api/v1/approvals/{ar.id}/approve",
            json={"decision_notes": "LGTM"},
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "approved"
        assert data["decision_notes"] == "LGTM"
        assert data["decided_by"] == str(reel48_admin_user.id)

        # Verify the underlying product status was also updated
        await admin_db_session.refresh(product)
        assert product.status == "approved"

    async def test_approve_order_via_unified_endpoint(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a1_employee,
    ):
        """Approve an order through the unified approval endpoint."""
        company, brand_a1, _a2 = company_a
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
        )
        ar = await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        response = await client.post(
            f"/api/v1/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "approved"

        # Verify the underlying order was also updated
        await admin_db_session.refresh(order)
        assert order.status == "approved"

    async def test_reject_order_via_unified_endpoint(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a1_employee,
    ):
        """Reject an order through the unified approval endpoint (cancels order)."""
        company, brand_a1, _a2 = company_a
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
        )
        ar = await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        response = await client.post(
            f"/api/v1/approvals/{ar.id}/reject",
            json={"decision_notes": "Over budget"},
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "rejected"
        assert data["decision_notes"] == "Over budget"

        # Verify the underlying order was cancelled
        await admin_db_session.refresh(order)
        assert order.status == "cancelled"

    async def test_cannot_approve_non_pending_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Cannot approve an already-decided request (returns 403)."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
            status="approved",
        )

        response = await client.post(
            f"/api/v1/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_approve(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_employee, user_a1_employee_token,
        user_a1_admin,
    ):
        """Employees get 403 on all approval decision endpoints."""
        company, brand_a1, _a2 = company_a
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
        )
        ar = await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        response = await client.post(
            f"/api/v1/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


# ===========================================================================
# Integration Tests: Submit/Create Records Approval Requests
# ===========================================================================


class TestIntegration:
    async def test_submitting_product_creates_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_admin_token,
    ):
        """Submitting a product creates an approval_request with entity_type='product'."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.post(
            f"/api/v1/products/{product.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200

        # Verify an approval_request was created
        result = await admin_db_session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == "product",
                ApprovalRequest.entity_id == product.id,
            )
        )
        ar = result.scalar_one_or_none()
        assert ar is not None
        assert ar.status == "pending"
        assert ar.requested_by == user_a1_admin.id

    async def test_submitting_catalog_creates_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_admin_token,
    ):
        """Submitting a catalog creates an approval_request with entity_type='catalog'."""
        company, brand_a1, _a2 = company_a
        catalog = await _create_submitted_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )
        # Reset to draft so we can submit via endpoint
        catalog.status = "draft"  # type: ignore[assignment]
        await admin_db_session.flush()

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200

        result = await admin_db_session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == "catalog",
                ApprovalRequest.entity_id == catalog.id,
            )
        )
        ar = result.scalar_one_or_none()
        assert ar is not None
        assert ar.status == "pending"

    async def test_creating_order_creates_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_employee, user_a1_employee_token,
        user_a1_admin,
    ):
        """Creating an order creates an approval_request with entity_type='order'."""
        company, brand_a1, _a2 = company_a
        catalog, product = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {
                        "product_id": str(product.id),
                        "quantity": 2,
                        "size": "M",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        order_id = response.json()["data"]["id"]

        result = await admin_db_session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == "order",
                ApprovalRequest.entity_id == order_id,
            )
        )
        ar = result.scalar_one_or_none()
        assert ar is not None
        assert ar.status == "pending"
        assert ar.requested_by == user_a1_employee.id

    async def test_submitting_bulk_order_creates_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a1_admin,
    ):
        """Submitting a bulk order creates an approval_request."""
        company, brand_a1, _a2 = company_a
        catalog, product = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )
        bulk_order = BulkOrder(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            catalog_id=catalog.id,
            created_by=user_a1_manager.id,
            title="Test Bulk Order",
            order_number=f"BLK-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}",
            status="draft",
            total_items=5,
            total_amount=Decimal("250.00"),
        )
        admin_db_session.add(bulk_order)
        await admin_db_session.flush()
        await admin_db_session.refresh(bulk_order)

        # Add at least one item (submit guard requires items)
        item = BulkOrderItem(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            bulk_order_id=bulk_order.id,
            product_id=product.id,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=Decimal("29.99"),
            quantity=5,
            line_total=Decimal("149.95"),
        )
        admin_db_session.add(item)
        await admin_db_session.flush()

        response = await client.post(
            f"/api/v1/bulk_orders/{bulk_order.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200

        result = await admin_db_session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == "bulk_order",
                ApprovalRequest.entity_id == bulk_order.id,
            )
        )
        ar = result.scalar_one_or_none()
        assert ar is not None
        assert ar.status == "pending"

    async def test_direct_platform_approve_syncs_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Approving via the direct platform endpoint also updates the approval_request."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        await admin_db_session.refresh(ar)
        assert ar.status == "approved"
        assert ar.decided_by == reel48_admin_user.id
        assert ar.decided_at is not None

    async def test_direct_platform_reject_syncs_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Rejecting via the direct platform endpoint also updates the approval_request."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/reject",
            json={"rejection_reason": "Bad quality"},
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        await admin_db_session.refresh(ar)
        assert ar.status == "rejected"
        assert ar.decision_notes == "Bad quality"

    async def test_direct_order_approve_syncs_approval_request(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a1_employee,
    ):
        """Approving an order via the direct endpoint also updates the approval_request."""
        company, brand_a1, _a2 = company_a
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
        )
        ar = await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        response = await client.post(
            f"/api/v1/orders/{order.id}/approve",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200

        await admin_db_session.refresh(ar)
        assert ar.status == "approved"
        assert ar.decided_by == user_a1_manager.id


# ===========================================================================
# Approval Rules Endpoint Tests
# ===========================================================================


class TestApprovalRulesEndpoints:
    async def test_create_approval_rule(
        self, client: AsyncClient,
        company_a, user_a_corporate_admin, user_a_corporate_admin_token,
    ):
        """Create an approval rule. Requires corporate_admin."""
        response = await client.post(
            "/api/v1/approval_rules/",
            json={
                "entity_type": "order",
                "rule_type": "amount_threshold",
                "threshold_amount": 500.00,
                "required_role": "corporate_admin",
            },
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["entity_type"] == "order"
        assert data["threshold_amount"] == 500.0
        assert data["required_role"] == "corporate_admin"
        assert data["is_active"] is True

    async def test_list_approval_rules(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a_corporate_admin, user_a_corporate_admin_token,
    ):
        """List approval rules for the company."""
        company, _a1, _a2 = company_a
        rule = ApprovalRule(
            company_id=company.id,
            entity_type="bulk_order",
            rule_type="amount_threshold",
            threshold_amount=Decimal("1000.00"),
            required_role="corporate_admin",
            is_active=True,
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(rule)
        await admin_db_session.flush()

        response = await client.get(
            "/api/v1/approval_rules/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1

    async def test_update_approval_rule(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a_corporate_admin, user_a_corporate_admin_token,
    ):
        """Update a rule's threshold and required_role."""
        company, _a1, _a2 = company_a
        rule = ApprovalRule(
            company_id=company.id,
            entity_type="order",
            rule_type="amount_threshold",
            threshold_amount=Decimal("200.00"),
            required_role="sub_brand_admin",
            is_active=True,
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(rule)
        await admin_db_session.flush()
        await admin_db_session.refresh(rule)

        response = await client.patch(
            f"/api/v1/approval_rules/{rule.id}",
            json={"threshold_amount": 750.0, "required_role": "corporate_admin"},
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["threshold_amount"] == 750.0
        assert data["required_role"] == "corporate_admin"

    async def test_deactivate_approval_rule(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a_corporate_admin, user_a_corporate_admin_token,
    ):
        """Deactivate a rule (soft: is_active=false). Returns 200."""
        company, _a1, _a2 = company_a
        rule = ApprovalRule(
            company_id=company.id,
            entity_type="order",
            rule_type="amount_threshold",
            threshold_amount=Decimal("300.00"),
            required_role="regional_manager",
            is_active=True,
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(rule)
        await admin_db_session.flush()
        await admin_db_session.refresh(rule)

        response = await client.delete(
            f"/api/v1/approval_rules/{rule.id}",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["is_active"] is False

    async def test_sub_brand_admin_gets_403_on_rules(
        self, client: AsyncClient,
        company_a, user_a1_admin_token,
    ):
        """Sub-brand admin cannot manage approval rules (requires corporate_admin)."""
        response = await client.get(
            "/api/v1/approval_rules/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_gets_403_on_rules(
        self, client: AsyncClient,
        company_a, user_a1_employee_token,
    ):
        response = await client.post(
            "/api/v1/approval_rules/",
            json={
                "entity_type": "order",
                "rule_type": "amount_threshold",
                "threshold_amount": 100.0,
                "required_role": "regional_manager",
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


class TestApprovalRulesEnforcementViaEndpoint:
    async def test_rule_blocks_manager_on_high_value_order(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_manager, user_a1_manager_token,
        user_a_corporate_admin, user_a1_employee,
    ):
        """Rule with required_role=corporate_admin blocks manager on high-value order."""
        company, brand_a1, _a2 = company_a

        # Create rule: orders over $500 require corporate_admin
        rule = ApprovalRule(
            company_id=company.id,
            entity_type="order",
            rule_type="amount_threshold",
            threshold_amount=Decimal("500.00"),
            required_role="corporate_admin",
            is_active=True,
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(rule)
        await admin_db_session.flush()

        # Create a $1000 order
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id,
            user_a1_employee.id, catalog.id,
            total_amount=Decimal("1000.00"),
        )
        ar = await _create_approval_request(
            admin_db_session, "order", order.id,
            company.id, brand_a1.id, user_a1_employee.id,
        )

        # Manager should be blocked
        response = await client.post(
            f"/api/v1/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403


# ===========================================================================
# Isolation Tests
# ===========================================================================


class TestApprovalIsolation:
    async def test_company_b_cannot_see_company_a_approval_queue(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a1_admin,
        user_b1_employee,
    ):
        """Company B cannot see Company A's pending approval requests."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Create a user in company B with admin role for the endpoint
        user_b_admin = User(
            company_id=company_b_obj.id,
            sub_brand_id=brand_b1.id,
            cognito_sub=str(uuid4()),
            email=f"admin-b-{uuid4().hex[:6]}@companyb.com",
            full_name="Admin B",
            role="sub_brand_admin",
        )
        admin_db_session.add(user_b_admin)
        await admin_db_session.flush()

        token_b = create_test_token(
            user_id=user_b_admin.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="sub_brand_admin",
        )

        # Create an approval request in Company A
        product = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company_a_obj.id, brand_a1.id, user_a1_admin.id,
        )

        # Query as Company B admin — should see no Company A requests
        response = await client.get(
            "/api/v1/approvals/pending/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        # All returned items should be from Company B (or empty)
        for item in data:
            assert item.get("entity_id") != str(product.id)

    async def test_company_b_cannot_manage_company_a_rules(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a_corporate_admin,
    ):
        """Company B admin cannot see Company A's approval rules."""
        company_a_obj, _a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Create a corporate admin for company B
        user_b_corp = User(
            company_id=company_b_obj.id,
            sub_brand_id=None,
            cognito_sub=str(uuid4()),
            email=f"corp-b-{uuid4().hex[:6]}@companyb.com",
            full_name="Corp Admin B",
            role="corporate_admin",
        )
        admin_db_session.add(user_b_corp)
        await admin_db_session.flush()

        token_b = create_test_token(
            user_id=user_b_corp.cognito_sub,
            company_id=str(company_b_obj.id),
            role="corporate_admin",
        )

        # Create a rule in Company A
        rule_a = ApprovalRule(
            company_id=company_a_obj.id,
            entity_type="order",
            rule_type="amount_threshold",
            threshold_amount=Decimal("500.00"),
            required_role="corporate_admin",
            is_active=True,
            created_by=user_a_corporate_admin.id,
        )
        admin_db_session.add(rule_a)
        await admin_db_session.flush()

        # Company B admin lists rules — should not see Company A's rules
        response = await client.get(
            "/api/v1/approval_rules/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        for r in data:
            assert r["company_id"] != str(company_a_obj.id)
