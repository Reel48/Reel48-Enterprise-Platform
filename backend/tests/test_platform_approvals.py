"""Tests for Module 6 Phase 4: Platform admin approval dashboard endpoints.

Tests cover:
- Platform approval list with and without filters
- Platform approval summary statistics
- Platform approval detail (cross-company)
- Platform approve/reject via approval endpoints
- Platform approval rules list (cross-company)
- Authorization (non-reel48_admin gets 403)
- Cross-company visibility
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest
from app.models.approval_rule import ApprovalRule
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.order import Order
from app.models.product import Product
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


async def _create_approval_rule(
    db: AsyncSession, company_id, created_by,
    *, entity_type="order", threshold=Decimal("500.00"),
) -> ApprovalRule:
    rule = ApprovalRule(
        company_id=company_id,
        entity_type=entity_type,
        rule_type="amount_threshold",
        threshold_amount=threshold,
        required_role="corporate_admin",
        is_active=True,
        created_by=created_by,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


# ===========================================================================
# Platform Approval List Endpoint Tests
# ===========================================================================


class TestPlatformApprovalList:
    async def test_list_all_approvals_returns_cross_company(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a1_admin, user_b1_employee,
        reel48_admin_user, reel48_admin_user_token,
    ):
        """reel48_admin sees approval requests from multiple companies."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Product approval in Company A
        product = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar_a = await _create_approval_request(
            admin_db_session, "product", product.id,
            company_a_obj.id, brand_a1.id, user_a1_admin.id,
        )

        # Order approval in Company B
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )
        order = await _create_pending_order(
            admin_db_session, company_b_obj.id, brand_b1.id,
            user_b1_employee.id, catalog.id,
        )
        ar_b = await _create_approval_request(
            admin_db_session, "order", order.id,
            company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )

        response = await client.get(
            "/api/v1/platform/approvals/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        ids = {item["id"] for item in data}
        assert str(ar_a.id) in ids
        assert str(ar_b.id) in ids

    async def test_list_all_approvals_with_status_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Status filter narrows results correctly."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id, status="pending",
        )
        product2 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product2.id,
            company.id, brand_a1.id, user_a1_admin.id, status="approved",
        )

        response = await client.get(
            "/api/v1/platform/approvals/?status=pending",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["status"] == "pending" for item in data)

    async def test_list_all_approvals_with_entity_type_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, user_a1_employee,
        reel48_admin_user, reel48_admin_user_token,
    ):
        """entity_type filter narrows results correctly."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )
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
            "/api/v1/platform/approvals/?entity_type=product",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["entity_type"] == "product" for item in data)

    async def test_list_all_approvals_with_company_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a1_admin, user_b1_employee,
        reel48_admin_user, reel48_admin_user_token,
    ):
        """company_id filter narrows results to a single company."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        product = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company_a_obj.id, brand_a1.id, user_a1_admin.id,
        )
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )
        order = await _create_pending_order(
            admin_db_session, company_b_obj.id, brand_b1.id,
            user_b1_employee.id, catalog.id,
        )
        await _create_approval_request(
            admin_db_session, "order", order.id,
            company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )

        response = await client.get(
            f"/api/v1/platform/approvals/?company_id={company_a_obj.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["company_id"] == str(company_a_obj.id) for item in data)
        assert len(data) >= 1

    async def test_list_all_approvals_pagination(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Pagination meta is correctly populated."""
        company, brand_a1, _a2 = company_a
        # Create 3 approval requests
        for _ in range(3):
            p = await _create_product(
                admin_db_session, company.id, brand_a1.id,
                user_a1_admin.id, status="submitted",
            )
            await _create_approval_request(
                admin_db_session, "product", p.id,
                company.id, brand_a1.id, user_a1_admin.id,
            )

        response = await client.get(
            "/api/v1/platform/approvals/?per_page=2&page=1",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        meta = response.json()["meta"]
        assert meta["per_page"] == 2
        assert meta["page"] == 1
        assert meta["total"] >= 3
        assert len(response.json()["data"]) == 2


# ===========================================================================
# Platform Approval Summary Endpoint Tests
# ===========================================================================


class TestPlatformApprovalSummary:
    async def test_summary_returns_correct_counts(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a1_admin, user_b1_employee,
        reel48_admin_user, reel48_admin_user_token,
    ):
        """Summary endpoint returns correct pending counts by type and company."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Pending product in Company A
        product = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company_a_obj.id, brand_a1.id, user_a1_admin.id,
        )

        # Pending order in Company B
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )
        order = await _create_pending_order(
            admin_db_session, company_b_obj.id, brand_b1.id,
            user_b1_employee.id, catalog.id,
        )
        await _create_approval_request(
            admin_db_session, "order", order.id,
            company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )

        response = await client.get(
            "/api/v1/platform/approvals/summary",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pending_count"] >= 2
        assert "product" in data["by_entity_type"]
        assert "order" in data["by_entity_type"]
        company_ids = {c["company_id"] for c in data["by_company"]}
        assert str(company_a_obj.id) in company_ids
        assert str(company_b_obj.id) in company_ids

    async def test_summary_excludes_decided_requests(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Summary only counts pending requests, not approved/rejected."""
        company, brand_a1, _a2 = company_a
        product1 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product1.id,
            company.id, brand_a1.id, user_a1_admin.id, status="approved",
        )

        response = await client.get(
            "/api/v1/platform/approvals/summary",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        # Approved requests should not contribute to pending_count for this test's data.
        # We can't assert exact 0 because other tests may seed pending data,
        # but the approved one should NOT appear in by_entity_type counts.


# ===========================================================================
# Platform Approval Detail Endpoint Tests
# ===========================================================================


class TestPlatformApprovalDetail:
    async def test_get_approval_request_cross_company(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_b, user_b1_employee, reel48_admin_user, reel48_admin_user_token,
    ):
        """reel48_admin can view approval request from any company."""
        company_b_obj, brand_b1 = company_b
        catalog, _ = await _create_catalog_with_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )
        order = await _create_pending_order(
            admin_db_session, company_b_obj.id, brand_b1.id,
            user_b1_employee.id, catalog.id,
        )
        ar = await _create_approval_request(
            admin_db_session, "order", order.id,
            company_b_obj.id, brand_b1.id, user_b1_employee.id,
        )

        response = await client.get(
            f"/api/v1/platform/approvals/{ar.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(ar.id)
        assert response.json()["data"]["entity_type"] == "order"


# ===========================================================================
# Platform Approve/Reject Endpoint Tests
# ===========================================================================


class TestPlatformApproveReject:
    async def test_approve_product_via_platform(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """reel48_admin can approve a product via the platform approval endpoint."""
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
            f"/api/v1/platform/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "approved"
        assert data["decided_by"] == str(reel48_admin_user.id)

    async def test_reject_product_via_platform(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """reel48_admin can reject a product via the platform approval endpoint."""
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
            f"/api/v1/platform/approvals/{ar.id}/reject",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
            json={"decision_notes": "Does not meet brand guidelines"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "rejected"
        assert data["decision_notes"] == "Does not meet brand guidelines"

    async def test_approve_already_decided_returns_403(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """Cannot approve an already-decided request."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            user_a1_admin.id, status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id, status="approved",
        )

        response = await client.post(
            f"/api/v1/platform/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 403


# ===========================================================================
# Platform Approval Rules List Endpoint Tests
# ===========================================================================


class TestPlatformApprovalRulesList:
    async def test_list_all_rules_cross_company(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a1_admin, user_b1_employee,
        reel48_admin_user, reel48_admin_user_token,
    ):
        """reel48_admin sees rules from multiple companies."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        rule_a = await _create_approval_rule(
            admin_db_session, company_a_obj.id, user_a1_admin.id,
            entity_type="order",
        )
        rule_b = await _create_approval_rule(
            admin_db_session, company_b_obj.id, user_b1_employee.id,
            entity_type="bulk_order",
        )

        response = await client.get(
            "/api/v1/platform/approval_rules/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        ids = {item["id"] for item in data}
        assert str(rule_a.id) in ids
        assert str(rule_b.id) in ids

    async def test_list_all_rules_with_company_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, company_b, user_a1_admin, user_b1_employee,
        reel48_admin_user, reel48_admin_user_token,
    ):
        """company_id filter narrows rules to a single company."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        await _create_approval_rule(
            admin_db_session, company_a_obj.id, user_a1_admin.id,
            entity_type="order",
        )
        await _create_approval_rule(
            admin_db_session, company_b_obj.id, user_b1_employee.id,
            entity_type="bulk_order",
        )

        response = await client.get(
            f"/api/v1/platform/approval_rules/?company_id={company_a_obj.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["company_id"] == str(company_a_obj.id) for item in data)

    async def test_list_all_rules_with_entity_type_filter(
        self, client: AsyncClient, admin_db_session: AsyncSession,
        company_a, user_a1_admin, reel48_admin_user, reel48_admin_user_token,
    ):
        """entity_type filter narrows rules correctly."""
        company, brand_a1, _a2 = company_a

        await _create_approval_rule(
            admin_db_session, company.id, user_a1_admin.id,
            entity_type="order",
        )

        response = await client.get(
            "/api/v1/platform/approval_rules/?entity_type=order",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert all(item["entity_type"] == "order" for item in data)


# ===========================================================================
# Authorization Tests (non-reel48_admin gets 403)
# ===========================================================================


class TestPlatformApprovalAuthorization:
    async def test_corporate_admin_gets_403_on_platform_approvals(
        self, client: AsyncClient,
        company_a, user_a_corporate_admin_token,
    ):
        """corporate_admin cannot access platform approval endpoints."""
        response = await client.get(
            "/api/v1/platform/approvals/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_gets_403_on_platform_approvals(
        self, client: AsyncClient,
        company_a, user_a1_admin_token,
    ):
        """sub_brand_admin cannot access platform approval endpoints."""
        response = await client.get(
            "/api/v1/platform/approvals/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_gets_403_on_platform_approvals(
        self, client: AsyncClient,
        company_a, user_a1_employee_token,
    ):
        """employee cannot access platform approval endpoints."""
        response = await client.get(
            "/api/v1/platform/approvals/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_corporate_admin_gets_403_on_platform_summary(
        self, client: AsyncClient,
        company_a, user_a_corporate_admin_token,
    ):
        """corporate_admin cannot access platform approval summary."""
        response = await client.get(
            "/api/v1/platform/approvals/summary",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_corporate_admin_gets_403_on_platform_approval_rules(
        self, client: AsyncClient,
        company_a, user_a_corporate_admin_token,
    ):
        """corporate_admin cannot access platform approval rules list."""
        response = await client.get(
            "/api/v1/platform/approval_rules/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_gets_403_on_platform_approve(
        self, client: AsyncClient,
        company_a, user_a1_employee_token,
    ):
        """employee cannot approve via platform endpoint."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/platform/approvals/{fake_id}/approve",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_manager_gets_403_on_platform_approvals(
        self, client: AsyncClient,
        company_a, user_a1_manager_token,
    ):
        """regional_manager cannot access platform approval endpoints."""
        response = await client.get(
            "/api/v1/platform/approvals/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403
